"""Main application window: a tab per toolkit module."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QTabWidget, QWidget

from fae_toolkit import __version__
from fae_toolkit.ui.battery_view import BatteryView
from fae_toolkit.ui.can_view import CanView
from fae_toolkit.ui.io_view import IoView
from fae_toolkit.ui.teaching_view import TeachingView


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
        self.io_view = IoView()
        self.can_view = CanView()
        self.teaching_view = TeachingView()
        tabs.addTab(self.battery_view, "① Battery (BMS)")
        tabs.addTab(self.io_view, "② IO / Modbus")
        tabs.addTab(self.can_view, "CAN (BMS)")
        tabs.addTab(self.teaching_view, "③ Teaching")
        self.setCentralWidget(tabs)
        self.statusBar().showMessage("Ready — select 'Simulator (no hardware)' and press Connect")

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self.battery_view.shutdown()
        self.io_view.shutdown()
        self.can_view.shutdown()
        self.teaching_view.shutdown()
        super().closeEvent(event)
