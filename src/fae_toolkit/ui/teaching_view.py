"""Teaching-point management panel.

An editable point table on the left and a live 2D map (nodes coloured by type,
routes drawn as polylines) on the right. Open/Save projects as JSON, export
points to CSV, and run validation — the teaching workflow as a desktop tool.
"""

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

_COLUMNS = ["id", "name", "type", "x", "y", "theta", "station"]
_TYPE_COLORS = {
    PointType.WAYPOINT: "#3498db",
    PointType.LOAD: "#27ae60",
    PointType.UNLOAD: "#e67e22",
    PointType.CHARGE: "#9b59b6",
    PointType.STANDBY: "#95a5a6",
}


class TeachingView(QWidget):
    """Self-contained teaching-point editor with a 2D map."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project = sample_project()
        self._loading = False
        self._build_ui()
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
        box = QGroupBox("프로젝트 (Project)")
        layout = QVBoxLayout(box)
        row1 = QHBoxLayout()
        for label, slot in [
            ("Sample", self._load_sample),
            ("Open…", self._open),
            ("Save…", self._save),
            ("Export CSV…", self._export_csv),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            row1.addWidget(btn)
        row2 = QHBoxLayout()
        for label, slot in [
            ("Add point", self._add_point),
            ("Delete point", self._delete_point),
            ("Validate", self._validate),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            row2.addWidget(btn)
        layout.addLayout(row1)
        layout.addLayout(row2)
        self.title_label = QLabel()
        layout.addWidget(self.title_label)
        return box

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
        box = QGroupBox("검증 / 로그 (Validation)")
        layout = QVBoxLayout(box)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(300)
        self.log_view.setFixedHeight(120)
        layout.addWidget(self.log_view)
        return box

    def _build_map(self) -> QWidget:
        pg.setConfigOptions(antialias=True)
        self.plot = pg.PlotWidget(title="Teaching map (mm)")
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
        path, _ = QFileDialog.getOpenFileName(self, "Open project", "", "JSON (*.json)")
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
            self, "Save project", "teaching.json", "JSON (*.json)"
        )
        if not path:
            return
        save_project(self._project, path)
        self._log(f"saved {path}")

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export points", "points.csv", "CSV (*.csv)")
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
                if col == 0:  # id is read-only
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

    # --- map rendering ---------------------------------------------------- #
    def _redraw_map(self) -> None:
        self.plot.clear()
        points = self._project.points
        by_id = {p.id: p for p in points}

        for route in self._project.routes:
            coords = [(by_id[i].x, by_id[i].y) for i in route.point_ids if i in by_id]
            if len(coords) >= 2:
                xs = [c[0] for c in coords]
                ys = [c[1] for c in coords]
                self.plot.plot(xs, ys, pen=pg.mkPen("#7f8c8d", width=2))

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
            ring = pg.ScatterPlotItem(
                [
                    {
                        "pos": (p.x, p.y),
                        "size": 26,
                        "brush": None,
                        "pen": pg.mkPen("#f1c40f", width=3),
                    }
                ]
            )
            self.plot.addItem(ring)

    def _log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def shutdown(self) -> None:  # symmetry with the other views
        pass
