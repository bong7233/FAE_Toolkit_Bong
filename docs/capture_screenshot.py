"""Render the GUI tabs to PNGs without a display (offscreen Qt).

Generates the README screenshots and acts as a quick visual smoke check::

    QT_QPA_PLATFORM=offscreen python docs/capture_screenshot.py
"""

from __future__ import annotations

import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from fae_toolkit.protocols.bms.model import BatteryFlag  # noqa: E402
from fae_toolkit.protocols.io import io_map  # noqa: E402
from fae_toolkit.ui.battery_view import SIM_LABEL  # noqa: E402
from fae_toolkit.ui.main_window import MainWindow  # noqa: E402


def _pump(app: QApplication, seconds: float) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.02)


def _capture_battery(app: QApplication, window: MainWindow, out: str) -> None:
    view = window.battery_view
    view.port_combo.setCurrentText(SIM_LABEL)
    view.interval_spin.setValue(100)
    view._connect()
    _pump(app, 2.0)
    if view._sim is not None:
        view._sim.set_load_current(-160.0)
        view._sim.force_warning(BatteryFlag.OVER_TEMP)
        view._log("scenario: heavy discharge + OVER_TEMP")
    _pump(app, 2.0)
    ok = window.grab().save(out, "PNG")
    print(f"battery: saved={ok} -> {out}")
    view.shutdown()


def _capture_io(app: QApplication, window: MainWindow, tabs, out: str) -> None:
    tabs.setCurrentIndex(1)
    view = window.io_view
    view.port_combo.setCurrentText(SIM_LABEL)
    view.interval_spin.setValue(100)
    view._connect()
    _pump(app, 1.2)
    view._on_output_clicked(io_map.DO_LOAD_CLAMP, True)
    view._on_output_clicked(io_map.DO_LIFT_UP, True)
    _pump(app, 1.2)
    if view._sim is not None:
        view._sim.trip_estop(True)
        view._log("scenario: E-STOP tripped — interlock open")
    _pump(app, 1.2)
    ok = window.grab().save(out, "PNG")
    print(f"io: saved={ok} -> {out}")
    view.shutdown()


def main() -> int:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.resize(1180, 720)
    window.show()
    tabs = window.centralWidget()
    _capture_battery(app, window, "docs/screenshot_battery.png")
    _capture_io(app, window, tabs, "docs/screenshot_io.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
