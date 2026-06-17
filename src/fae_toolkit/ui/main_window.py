"""Main application window: a tab per toolkit module."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QTabWidget, QWidget

from fae_toolkit import __version__
from fae_toolkit.ui.battery_view import BatteryView


def _placeholder(text: str) -> QWidget:
    widget = QLabel(text)
    widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
    widget.setStyleSheet("color:#888; font-size:16px;")
    return widget


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"FAE Toolkit v{__version__}")
        self.resize(1180, 720)

        tabs = QTabWidget()
        self.battery_view = BatteryView()
        tabs.addTab(self.battery_view, "① Battery (BMS)")
        tabs.addTab(_placeholder("🚧 IO / Modbus 통신 테스트 — coming soon"), "② IO / Modbus")
        tabs.addTab(_placeholder("🚧 티칭 포인트 관리(심화) — coming soon"), "③ Teaching")
        self.setCentralWidget(tabs)
        self.statusBar().showMessage("Ready — select 'Simulator (no hardware)' and press Connect")

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self.battery_view.shutdown()
        super().closeEvent(event)
