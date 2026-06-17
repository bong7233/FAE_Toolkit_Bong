"""Render the GUI to a PNG without a display (offscreen Qt).

Used to generate the README screenshot and as a quick visual smoke check::

    QT_QPA_PLATFORM=offscreen python docs/capture_screenshot.py docs/screenshot_battery.png
"""

from __future__ import annotations

import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from fae_toolkit.protocols.bms.model import BatteryFlag  # noqa: E402
from fae_toolkit.ui.battery_view import SIM_LABEL  # noqa: E402
from fae_toolkit.ui.main_window import MainWindow  # noqa: E402


def _pump(app: QApplication, seconds: float) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.02)


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else "docs/screenshot_battery.png"
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.resize(1180, 720)
    window.show()

    view = window.battery_view
    view.port_combo.setCurrentText(SIM_LABEL)
    view.interval_spin.setValue(100)
    view._connect()
    _pump(app, 2.0)

    # Drive an interesting trend and raise an alarm for the screenshot.
    if view._sim is not None:
        view._sim.set_load_current(-160.0)
        view._sim.force_warning(BatteryFlag.OVER_TEMP)
        view._log("scenario: heavy discharge + OVER_TEMP")
    _pump(app, 2.0)

    pixmap = window.grab()
    saved = pixmap.save(out, "PNG")
    print(f"saved={saved} path={out} size={pixmap.width()}x{pixmap.height()}")
    view.shutdown()
    return 0 if saved else 1


if __name__ == "__main__":
    sys.exit(main())
