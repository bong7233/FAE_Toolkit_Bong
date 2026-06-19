"""Teaching-point editor: table + interactive 2D map over a CAD/floor-plan.

Markers encode two dimensions at a glance:
* **shape + outline colour** = equipment type (user-customisable in the Types tab)
* **fill colour** = teaching status (in-progress / done / alarm)

A background image (an exported CAD drawing or floor plan) can be placed under
the points so teaching happens in real layout context.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import (
    QAbstractItemView,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from fae_toolkit.teaching import (
    SHAPES,
    BackgroundImage,
    EquipmentStyle,
    TeachingPoint,
    TeachingStatus,
    export_points_csv,
    load_project,
    sample_project,
    save_project,
    validate,
)
from fae_toolkit.ui.i18n import i18n, tr

_COLUMNS = ["id", "name", "type", "x", "y", "theta", "station", "status"]
_COL_KEYS = {
    "id": "tm.col_id",
    "name": "tm.col_name",
    "type": "tm.col_type",
    "x": "tm.col_x",
    "y": "tm.col_y",
    "theta": "tm.col_theta",
    "station": "tm.col_station",
    "status": "tm.col_status",
}
# editable plain-text columns -> model attribute
_TEXT_FIELDS = {1: "name", 3: "x", 4: "y", 5: "theta", 6: "station"}

_STATUS_FILL = {
    TeachingStatus.IN_PROGRESS: "#f1c40f",
    TeachingStatus.DONE: "#2ecc71",
    TeachingStatus.ALARM: "#e74c3c",
}
_STATUS_KEY = {
    TeachingStatus.IN_PROGRESS: "tm.status_in_progress",
    TeachingStatus.DONE: "tm.status_done",
    TeachingStatus.ALARM: "tm.status_alarm",
}
_SHAPE_SYMBOL = {
    "circle": "o",
    "square": "s",
    "triangle": "t",
    "diamond": "d",
    "star": "star",
    "plus": "+",
    "cross": "x",
}

_QSS = """
QWidget#teachingRoot { background: #f4f6f8; }
QGroupBox, QTabWidget::pane { border: 1px solid #d4dae0; border-radius: 8px; }
QTabWidget::pane { background: #ffffff; top: -1px; }
QTabBar::tab {
    background: #e9edf1; padding: 6px 14px; margin-right: 2px;
    border-top-left-radius: 6px; border-top-right-radius: 6px; color: #4a5560;
}
QTabBar::tab:selected { background: #ffffff; color: #1f6feb; font-weight: bold; }
QPushButton {
    background: #ffffff; border: 1px solid #cbd2d9; border-radius: 6px;
    padding: 6px 12px; color: #2c3e50;
}
QPushButton:hover { border-color: #1f6feb; color: #1f6feb; }
QPushButton:pressed { background: #eef4ff; }
QTableWidget {
    background: #ffffff; border: 1px solid #d4dae0; border-radius: 8px;
    gridline-color: #eceff2; selection-background-color: #dbeafe; selection-color: #111;
}
QHeaderView::section {
    background: #eef1f4; padding: 6px; border: none; border-right: 1px solid #e2e6ea;
    color: #55606b; font-weight: bold;
}
QPlainTextEdit {
    background: #0f1720; color: #d6e2ee; border-radius: 8px; border: 1px solid #243140;
    font-family: monospace;
}
"""


def _chip(text: str, color: str) -> QLabel:
    chip = QLabel(text)
    chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
    chip.setStyleSheet(
        f"background:{color}; color:white; border-radius:10px; padding:6px 10px; font-weight:bold;"
    )
    return chip


class TeachingView(QWidget):
    """Editable teaching points on the left, a live 2D map on the right."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project = sample_project()
        self._loading = False
        self.setObjectName("teachingRoot")
        self.setStyleSheet(_QSS)
        pg.setConfigOption("imageAxisOrder", "row-major")
        self._build_ui()
        i18n.subscribe(self.retranslate)
        self.retranslate()
        self._reload()

    # --- UI construction -------------------------------------------------- #
    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        left = QVBoxLayout()
        left.addLayout(self._build_toolbar())
        left.addLayout(self._build_dashboard())
        left.addWidget(self._build_table(), stretch=1)
        left.addWidget(self._build_bottom_tabs())
        root.addLayout(left, stretch=3)
        root.addWidget(self._build_map(), stretch=5)

    def _build_toolbar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        self.btn_sample = QPushButton()
        self.btn_sample.clicked.connect(self._load_sample)
        self.btn_open = QPushButton()
        self.btn_open.clicked.connect(self._open)
        self.btn_save = QPushButton()
        self.btn_save.clicked.connect(self._save)
        self.btn_export = QPushButton()
        self.btn_export.clicked.connect(self._export_csv)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        self.btn_add = QPushButton()
        self.btn_add.clicked.connect(self._add_point)
        self.btn_delete = QPushButton()
        self.btn_delete.clicked.connect(self._delete_point)
        self.btn_validate = QPushButton()
        self.btn_validate.clicked.connect(self._validate)
        for b in (self.btn_sample, self.btn_open, self.btn_save, self.btn_export):
            bar.addWidget(b)
        bar.addWidget(sep)
        for b in (self.btn_add, self.btn_delete, self.btn_validate):
            bar.addWidget(b)
        bar.addStretch(1)
        return bar

    def _build_dashboard(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.chip_total = _chip("", "#34495e")
        self.chip_done = _chip("", _STATUS_FILL[TeachingStatus.DONE])
        self.chip_prog = _chip("", _STATUS_FILL[TeachingStatus.IN_PROGRESS])
        self.chip_alarm = _chip("", _STATUS_FILL[TeachingStatus.ALARM])
        for c in (self.chip_total, self.chip_done, self.chip_prog, self.chip_alarm):
            row.addWidget(c)
        row.addStretch(1)
        return row

    def _build_table(self) -> QTableWidget:
        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.itemSelectionChanged.connect(self._redraw_map)
        return self.table

    def _build_bottom_tabs(self) -> QTabWidget:
        self.tabs = QTabWidget()
        self.tabs.setMaximumHeight(190)
        self.tabs.addTab(self._build_background_tab(), "")
        self.tabs.addTab(self._build_types_tab(), "")
        self.tabs.addTab(self._build_log_tab(), "")
        return self.tabs

    def _build_background_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        row = QHBoxLayout()
        self.btn_bg_load = QPushButton()
        self.btn_bg_load.clicked.connect(self._load_background)
        self.btn_bg_clear = QPushButton()
        self.btn_bg_clear.clicked.connect(self._clear_background)
        self.bg_path_label = QLabel()
        self.bg_path_label.setStyleSheet("color:#55606b;")
        row.addWidget(self.btn_bg_load)
        row.addWidget(self.btn_bg_clear)
        row.addWidget(self.bg_path_label, stretch=1)
        layout.addLayout(row)

        row2 = QHBoxLayout()
        self.lbl_opacity = QLabel()
        self.sld_opacity = QSlider(Qt.Orientation.Horizontal)
        self.sld_opacity.setRange(10, 100)
        self.sld_opacity.setValue(50)
        self.sld_opacity.valueChanged.connect(self._on_bg_opacity)
        self.lbl_scale = QLabel()
        self.spn_scale = QDoubleSpinBox()
        self.spn_scale.setRange(0.1, 1000.0)
        self.spn_scale.setValue(10.0)
        self.spn_scale.setSingleStep(0.5)
        self.spn_scale.valueChanged.connect(self._on_bg_scale)
        row2.addWidget(self.lbl_opacity)
        row2.addWidget(self.sld_opacity, stretch=1)
        row2.addWidget(self.lbl_scale)
        row2.addWidget(self.spn_scale)
        layout.addLayout(row2)

        self.bg_hint = QLabel()
        self.bg_hint.setWordWrap(True)
        self.bg_hint.setStyleSheet("color:#8a949e; font-size:11px;")
        layout.addWidget(self.bg_hint)
        layout.addStretch(1)
        return w

    def _build_types_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.types_table = QTableWidget(0, 3)
        self.types_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.types_table.verticalHeader().setVisible(False)
        layout.addWidget(self.types_table, stretch=1)
        row = QHBoxLayout()
        self.btn_type_add = QPushButton()
        self.btn_type_add.clicked.connect(self._add_type)
        self.btn_type_remove = QPushButton()
        self.btn_type_remove.clicked.connect(self._remove_type)
        row.addWidget(self.btn_type_add)
        row.addWidget(self.btn_type_remove)
        row.addStretch(1)
        layout.addLayout(row)
        return w

    def _build_log_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(300)
        layout.addWidget(self.log_view)
        return w

    def _build_map(self) -> QWidget:
        pg.setConfigOptions(antialias=True)
        self.plot = pg.PlotWidget()
        self.plot.setBackground("#fbfcfd")
        self.plot.setAspectLocked(True)
        self.plot.showGrid(x=True, y=True, alpha=0.25)
        self.plot.setLabel("bottom", "X", "mm")
        self.plot.setLabel("left", "Y", "mm")
        self.plot.getAxis("bottom").enableAutoSIPrefix(False)
        self.plot.getAxis("left").enableAutoSIPrefix(False)
        return self.plot

    # --- project actions -------------------------------------------------- #
    def _load_sample(self) -> None:
        self._project = sample_project()
        self._reload()
        self._log("loaded sample project")

    def _open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("tm.btn_open"), "", "JSON (*.json)")
        if not path:
            return
        try:
            self._project = load_project(path)
        except Exception as exc:
            self._log(f"open failed: {exc}")
            return
        self._reload()
        self._log(f"opened {path}")

    def _save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, tr("tm.btn_save"), "teaching.json", "JSON (*.json)"
        )
        if not path:
            return
        save_project(self._project, path)
        self._log(f"saved {path}")

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, tr("tm.btn_export"), "points.csv", "CSV (*.csv)"
        )
        if not path:
            return
        export_points_csv(self._project, path)
        self._log(f"exported {path}")

    def _add_point(self) -> None:
        new_id = self._project.next_id()
        self._project.add_point(TeachingPoint(new_id, f"P{new_id}", "WAYPOINT", 0.0, 0.0))
        self._reload()
        self._log(f"added point {new_id}")

    def _delete_point(self) -> None:
        point_id = self._selected_point_id()
        if point_id is None:
            return
        self._project.remove_point(point_id)
        self._reload()
        self._log(f"deleted point {point_id}")

    def _validate(self) -> None:
        issues = validate(self._project)
        if not issues:
            self._log("validation: OK (no issues)")
        else:
            self._log(f"validation: {len(issues)} issue(s)")
            for issue in issues:
                self._log(f"  - {issue}")
        self.tabs.setCurrentIndex(2)

    # --- background ------------------------------------------------------- #
    def _load_background(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("tm.bg_load"), "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if not path:
            return
        self._project.background = BackgroundImage(
            path=path, scale=self.spn_scale.value(), opacity=self.sld_opacity.value() / 100.0
        )
        self._refresh_bg_label()
        self._redraw_map()
        self._log(f"background: {path}")

    def _clear_background(self) -> None:
        self._project.background = None
        self._refresh_bg_label()
        self._redraw_map()

    def _on_bg_opacity(self, value: int) -> None:
        if self._project.background:
            self._project.background.opacity = value / 100.0
            self._redraw_map()

    def _on_bg_scale(self, value: float) -> None:
        if self._project.background:
            self._project.background.scale = value
            self._redraw_map()

    def _refresh_bg_label(self) -> None:
        bg = self._project.background
        if bg:
            import os

            self.bg_path_label.setText(os.path.basename(bg.path))
            self.sld_opacity.blockSignals(True)
            self.spn_scale.blockSignals(True)
            self.sld_opacity.setValue(int(bg.opacity * 100))
            self.spn_scale.setValue(bg.scale)
            self.sld_opacity.blockSignals(False)
            self.spn_scale.blockSignals(False)
        else:
            self.bg_path_label.setText(tr("tm.bg_none"))

    def _background_item(self) -> pg.ImageItem | None:
        bg = self._project.background
        if not bg:
            return None
        img = QImage(bg.path)
        if img.isNull():
            self._log(f"could not load image: {bg.path}")
            return None
        img = img.convertToFormat(QImage.Format.Format_RGBA8888)
        w, h = img.width(), img.height()
        buf = img.constBits()
        arr = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 4)
        arr = np.ascontiguousarray(arr[::-1])  # flip Y so it renders upright in a Y-up plot
        item = pg.ImageItem(arr)
        item.setRect(QRectF(bg.x, bg.y, w * bg.scale, h * bg.scale))
        item.setOpacity(bg.opacity)
        item.setZValue(-100)
        return item

    # --- equipment types editor ------------------------------------------ #
    def _reload_types(self) -> None:
        self._loading = True
        styles = self._project.styles
        self.types_table.setRowCount(len(styles))
        for row, style in enumerate(styles):
            name_item = QTableWidgetItem(style.type)
            self.types_table.setItem(row, 0, name_item)

            color_btn = QPushButton(style.color)
            color_btn.setStyleSheet(
                f"background:{style.color}; color:white; border-radius:4px; padding:4px;"
            )
            color_btn.setProperty("type_name", style.type)
            color_btn.clicked.connect(self._pick_color)
            self.types_table.setCellWidget(row, 1, color_btn)

            shape_combo = QComboBox()
            for shp in SHAPES:
                shape_combo.addItem(tr(f"tm.shape_{shp}"), shp)
            cur_shape = style.shape if style.shape in SHAPES else "circle"
            shape_combo.setCurrentIndex(list(SHAPES).index(cur_shape))
            shape_combo.setProperty("type_name", style.type)
            shape_combo.currentIndexChanged.connect(self._on_shape_changed)
            self.types_table.setCellWidget(row, 2, shape_combo)
        self.types_table.setHorizontalHeaderLabels(
            [tr("tm.col_type"), tr("tm.col_color"), tr("tm.col_shape")]
        )
        self._loading = False

    def _add_type(self) -> None:
        name, ok = QInputDialog.getText(self, tr("tm.types_add"), tr("tm.types_new_prompt"))
        name = name.strip()
        if not ok or not name or self._project.style_for(name).type == name:
            return
        self._project.styles.append(EquipmentStyle(name, "#1abc9c", "circle"))
        self._reload_types()
        self._refresh_type_combos()
        self._log(f"added type {name}")

    def _remove_type(self) -> None:
        rows = self.types_table.selectionModel().selectedRows()
        if not rows:
            return
        idx = rows[0].row()
        if 0 <= idx < len(self._project.styles):
            removed = self._project.styles.pop(idx)
            self._reload_types()
            self._refresh_type_combos()
            self._redraw_map()
            self._log(f"removed type {removed.type}")

    def _pick_color(self) -> None:
        btn = self.sender()
        type_name = btn.property("type_name")
        style = self._project.style_for(type_name)
        chosen = QColorDialog.getColor(QColor(style.color), self, tr("tm.col_color"))
        if chosen.isValid():
            style.color = chosen.name()
            self._reload_types()
            self._redraw_map()

    def _on_shape_changed(self, _index: int) -> None:
        if self._loading:
            return
        combo = self.sender()
        type_name = combo.property("type_name")
        self._project.style_for(type_name).shape = combo.currentData()
        self._redraw_map()

    # --- table <-> model -------------------------------------------------- #
    def _reload(self) -> None:
        self._loading = True
        self.table.setRowCount(len(self._project.points))
        for row, p in enumerate(self._project.points):
            self._set_text(row, 0, str(p.id), editable=False)
            self._set_text(row, 1, p.name)
            self._set_type_combo(row, p)
            self._set_text(row, 3, _num(p.x))
            self._set_text(row, 4, _num(p.y))
            self._set_text(row, 5, _num(p.theta))
            self._set_text(row, 6, p.station)
            self._set_status_combo(row, p)
        self._loading = False
        self._refresh_bg_label()
        self._reload_types()
        self._update_dashboard()
        self._redraw_map()

    def _set_text(self, row: int, col: int, value: str, editable: bool = True) -> None:
        item = QTableWidgetItem(value)
        if not editable:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, col, item)

    def _set_type_combo(self, row: int, p: TeachingPoint) -> None:
        combo = QComboBox()
        combo.setEditable(True)
        types = self._project.types()
        combo.addItems(types)
        combo.setCurrentText(p.type)
        combo.setProperty("pid", p.id)
        combo.currentTextChanged.connect(self._on_type_changed)
        self.table.setCellWidget(row, 2, combo)

    def _set_status_combo(self, row: int, p: TeachingPoint) -> None:
        combo = QComboBox()
        for status in TeachingStatus:
            combo.addItem(tr(_STATUS_KEY[status]), status.value)
        combo.setCurrentIndex(list(TeachingStatus).index(p.status))
        combo.setProperty("pid", p.id)
        self._style_status_combo(combo, p.status)
        combo.currentIndexChanged.connect(self._on_status_changed)
        self.table.setCellWidget(row, 7, combo)

    @staticmethod
    def _style_status_combo(combo: QComboBox, status: TeachingStatus) -> None:
        combo.setStyleSheet(
            f"background:{_STATUS_FILL[status]}; color:white; font-weight:bold; border-radius:4px;"
        )

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading:
            return
        field = _TEXT_FIELDS.get(item.column())
        if field is None:
            return
        point = self._project.points[item.row()]
        text = item.text().strip()
        try:
            if field in ("x", "y", "theta"):
                setattr(point, field, float(text))
            else:
                setattr(point, field, text)
        except ValueError:
            self._log(f"invalid {field}: '{text}' (reverted)")
            self._reload()
            return
        self._redraw_map()

    def _on_type_changed(self, text: str) -> None:
        if self._loading:
            return
        combo = self.sender()
        point = self._project.get_point(combo.property("pid"))
        if point is None:
            return
        text = text.strip()
        point.type = text or "WAYPOINT"
        if text and self._project.style_for(text).type != text:
            self._project.styles.append(EquipmentStyle(text, "#1abc9c", "circle"))
            self._reload_types()
        self._redraw_map()

    def _on_status_changed(self, _index: int) -> None:
        if self._loading:
            return
        combo = self.sender()
        point = self._project.get_point(combo.property("pid"))
        if point is None:
            return
        point.status = TeachingStatus(combo.currentData())
        self._style_status_combo(combo, point.status)
        self._update_dashboard()
        self._redraw_map()

    def _selected_point_id(self) -> int | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        return self._project.points[rows[0].row()].id

    # --- dashboard -------------------------------------------------------- #
    def _update_dashboard(self) -> None:
        pts = self._project.points
        done = sum(1 for p in pts if p.status == TeachingStatus.DONE)
        prog = sum(1 for p in pts if p.status == TeachingStatus.IN_PROGRESS)
        alarm = sum(1 for p in pts if p.status == TeachingStatus.ALARM)
        self.chip_total.setText(f"{tr('tm.dash_total')}: {len(pts)}")
        self.chip_done.setText(f"{tr('tm.status_done')}: {done}")
        self.chip_prog.setText(f"{tr('tm.status_in_progress')}: {prog}")
        self.chip_alarm.setText(f"{tr('tm.status_alarm')}: {alarm}")

    def _refresh_type_combos(self) -> None:
        # Rebuild the per-row type combos so newly added types appear.
        self._reload()

    # --- map -------------------------------------------------------------- #
    def _redraw_map(self) -> None:
        self.plot.clear()
        bg_item = self._background_item()
        if bg_item is not None:
            self.plot.addItem(bg_item)

        points = self._project.points
        by_id = {p.id: p for p in points}
        for route in self._project.routes:
            coords = [(by_id[i].x, by_id[i].y) for i in route.point_ids if i in by_id]
            if len(coords) >= 2:
                self.plot.plot(
                    [c[0] for c in coords],
                    [c[1] for c in coords],
                    pen=pg.mkPen("#90a4ae", width=2, style=Qt.PenStyle.DashLine),
                )
        if points:
            spots = []
            for p in points:
                style = self._project.style_for(p.type)
                spots.append(
                    {
                        "pos": (p.x, p.y),
                        "symbol": _SHAPE_SYMBOL.get(style.shape, "o"),
                        "brush": pg.mkBrush(_STATUS_FILL[p.status]),
                        "pen": pg.mkPen(style.color, width=3),
                        "size": 18,
                    }
                )
            self.plot.addItem(pg.ScatterPlotItem(spots=spots))
            for p in points:
                label = pg.TextItem(p.name, color="#34495e", anchor=(0, 1))
                label.setPos(p.x, p.y)
                self.plot.addItem(label)

        selected = self._selected_point_id()
        if selected is not None and selected in by_id:
            p = by_id[selected]
            ring = {
                "pos": (p.x, p.y),
                "size": 30,
                "brush": None,
                "pen": pg.mkPen("#1f6feb", width=3),
            }
            self.plot.addItem(pg.ScatterPlotItem([ring]))

    def _log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def retranslate(self) -> None:
        self.btn_sample.setText(tr("tm.btn_sample"))
        self.btn_open.setText(tr("tm.btn_open"))
        self.btn_save.setText(tr("tm.btn_save"))
        self.btn_export.setText(tr("tm.btn_export"))
        self.btn_add.setText(tr("tm.btn_add"))
        self.btn_delete.setText(tr("tm.btn_delete"))
        self.btn_validate.setText(tr("tm.btn_validate"))
        self.table.setHorizontalHeaderLabels([tr(_COL_KEYS[c]) for c in _COLUMNS])
        self.tabs.setTabText(0, tr("tm.tab_background"))
        self.tabs.setTabText(1, tr("tm.tab_types"))
        self.tabs.setTabText(2, tr("tm.tab_log"))
        self.btn_bg_load.setText(tr("tm.bg_load"))
        self.btn_bg_clear.setText(tr("tm.bg_clear"))
        self.lbl_opacity.setText(tr("tm.bg_opacity"))
        self.lbl_scale.setText(tr("tm.bg_scale"))
        self.bg_hint.setText(tr("tm.bg_hint"))
        self.btn_type_add.setText(tr("tm.types_add"))
        self.btn_type_remove.setText(tr("tm.types_remove"))
        self.plot.setTitle(tr("tm.map_title"))
        self._refresh_bg_label()
        self._reload_types()
        self._update_dashboard()

    def shutdown(self) -> None:
        pass


def _num(value: float) -> str:
    """Format a float without a trailing ``.0`` for whole numbers."""
    return str(int(value)) if float(value).is_integer() else str(value)
