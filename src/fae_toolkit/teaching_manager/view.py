"""Teaching-point editor widget (table + 2D map), i18n-aware."""

from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from fae_toolkit.teaching import (
    PointType,
    TeachingPoint,
    export_points_csv,
    load_project,
    sample_project,
    save_project,
    validate,
)
from fae_toolkit.ui.i18n import i18n, tr

_COLUMNS = ["id", "name", "type", "x", "y", "theta", "station"]
_TYPE_COLORS = {
    PointType.WAYPOINT: "#3498db",
    PointType.LOAD: "#27ae60",
    PointType.UNLOAD: "#e67e22",
    PointType.CHARGE: "#9b59b6",
    PointType.STANDBY: "#95a5a6",
}


class TeachingView(QWidget):
    """Editable teaching points on the left, a live 2D map on the right."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project = sample_project()
        self._loading = False
        self._build_ui()
        i18n.subscribe(self.retranslate)
        self.retranslate()
        self._reload()

    # --- UI construction -------------------------------------------------- #
    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        left = QVBoxLayout()
        left.addWidget(self._build_toolbar())
        left.addWidget(self._build_table(), stretch=1)
        left.addWidget(self._build_log())
        root.addLayout(left, stretch=0)
        root.addWidget(self._build_map(), stretch=1)

    def _build_toolbar(self) -> QGroupBox:
        self.toolbar_box = QGroupBox()
        layout = QVBoxLayout(self.toolbar_box)
        row1 = QHBoxLayout()
        self.btn_sample = QPushButton()
        self.btn_sample.clicked.connect(self._load_sample)
        self.btn_open = QPushButton()
        self.btn_open.clicked.connect(self._open)
        self.btn_save = QPushButton()
        self.btn_save.clicked.connect(self._save)
        self.btn_export = QPushButton()
        self.btn_export.clicked.connect(self._export_csv)
        for b in (self.btn_sample, self.btn_open, self.btn_save, self.btn_export):
            row1.addWidget(b)
        row2 = QHBoxLayout()
        self.btn_add = QPushButton()
        self.btn_add.clicked.connect(self._add_point)
        self.btn_delete = QPushButton()
        self.btn_delete.clicked.connect(self._delete_point)
        self.btn_validate = QPushButton()
        self.btn_validate.clicked.connect(self._validate)
        for b in (self.btn_add, self.btn_delete, self.btn_validate):
            row2.addWidget(b)
        layout.addLayout(row1)
        layout.addLayout(row2)
        self.title_label = QLabel()
        layout.addWidget(self.title_label)
        return self.toolbar_box

    def _build_table(self) -> QTableWidget:
        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setHorizontalHeaderLabels(_COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.itemSelectionChanged.connect(self._redraw_map)
        return self.table

    def _build_log(self) -> QGroupBox:
        self.log_box = QGroupBox()
        layout = QVBoxLayout(self.log_box)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(300)
        self.log_view.setFixedHeight(120)
        layout.addWidget(self.log_view)
        return self.log_box

    def _build_map(self) -> QWidget:
        pg.setConfigOptions(antialias=True)
        self.plot = pg.PlotWidget()
        self.plot.setAspectLocked(True)
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.setLabel("bottom", "X", "mm")
        self.plot.setLabel("left", "Y", "mm")
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
        self._project.add_point(TeachingPoint(new_id, f"P{new_id}", PointType.WAYPOINT, 0.0, 0.0))
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

    # --- table <-> model -------------------------------------------------- #
    def _reload(self) -> None:
        self._loading = True
        self.table.setRowCount(len(self._project.points))
        for row, p in enumerate(self._project.points):
            values = [p.id, p.name, p.type.value, p.x, p.y, p.theta, p.station]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col == 0:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)
        self._loading = False
        self.title_label.setText(
            f"'{self._project.name}'  ·  {len(self._project.points)} points  ·  "
            f"{len(self._project.routes)} routes"
        )
        self._redraw_map()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading:
            return
        point = self._project.points[item.row()]
        field = _COLUMNS[item.column()]
        text = item.text().strip()
        try:
            if field == "name":
                point.name = text
            elif field == "type":
                point.type = PointType(text.upper())
            elif field == "station":
                point.station = text
            elif field in ("x", "y", "theta"):
                setattr(point, field, float(text))
        except (ValueError, KeyError):
            self._log(f"invalid {field}: '{text}' (reverted)")
            self._reload()
            return
        self._redraw_map()

    def _selected_point_id(self) -> int | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        return self._project.points[rows[0].row()].id

    # --- map -------------------------------------------------------------- #
    def _redraw_map(self) -> None:
        self.plot.clear()
        points = self._project.points
        by_id = {p.id: p for p in points}
        for route in self._project.routes:
            coords = [(by_id[i].x, by_id[i].y) for i in route.point_ids if i in by_id]
            if len(coords) >= 2:
                self.plot.plot(
                    [c[0] for c in coords], [c[1] for c in coords], pen=pg.mkPen("#7f8c8d", width=2)
                )
        if points:
            spots = [
                {
                    "pos": (p.x, p.y),
                    "brush": pg.mkBrush(_TYPE_COLORS.get(p.type, "#3498db")),
                    "size": 16,
                    "pen": pg.mkPen("#222"),
                }
                for p in points
            ]
            self.plot.addItem(pg.ScatterPlotItem(spots=spots))
            for p in points:
                label = pg.TextItem(p.name, color="#ddd", anchor=(0, 1))
                label.setPos(p.x, p.y)
                self.plot.addItem(label)
        selected = self._selected_point_id()
        if selected is not None and selected in by_id:
            p = by_id[selected]
            self.plot.addItem(
                pg.ScatterPlotItem(
                    [
                        {
                            "pos": (p.x, p.y),
                            "size": 26,
                            "brush": None,
                            "pen": pg.mkPen("#f1c40f", width=3),
                        }
                    ]
                )
            )

    def _log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def retranslate(self) -> None:
        self.toolbar_box.setTitle(tr("tm.group_project"))
        self.log_box.setTitle(tr("tm.group_validation"))
        self.btn_sample.setText(tr("tm.btn_sample"))
        self.btn_open.setText(tr("tm.btn_open"))
        self.btn_save.setText(tr("tm.btn_save"))
        self.btn_export.setText(tr("tm.btn_export"))
        self.btn_add.setText(tr("tm.btn_add"))
        self.btn_delete.setText(tr("tm.btn_delete"))
        self.btn_validate.setText(tr("tm.btn_validate"))
        self.plot.setTitle(tr("tm.map_title"))

    def shutdown(self) -> None:
        pass
