"""Render an animated GIF of the battery module to docs/demo_battery.gif.

Offscreen (no display required)::

    QT_QPA_PLATFORM=offscreen python docs/capture_gif.py
"""

from __future__ import annotations

import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image  # noqa: E402
from PySide6.QtGui import QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from fae_toolkit.protocols.bms.model import BatteryFlag  # noqa: E402
from fae_toolkit.ui.battery_view import SIM_LABEL  # noqa: E402
from fae_toolkit.ui.main_window import MainWindow  # noqa: E402

_FRAME_W = 600


def _grab(window) -> Image.Image:
    qimg = window.grab().toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    buf = bytes(qimg.constBits())
    img = Image.frombytes("RGBA", (qimg.width(), qimg.height()), buf)
    ratio = _FRAME_W / img.width
    return img.resize((_FRAME_W, int(img.height * ratio))).convert("RGB")


def _pump(app, seconds: float) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.02)


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else "docs/demo_battery.gif"
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.resize(1180, 720)
    window.show()

    view = window.battery_view
    view.port_combo.setCurrentText(SIM_LABEL)
    view.interval_spin.setValue(120)
    view._connect()

    frames: list[Image.Image] = []
    for i in range(22):
        if i == 11 and view._sim is not None:
            view._sim.set_load_current(-160.0)
            view._sim.force_warning(BatteryFlag.OVER_TEMP)
            view._log("scenario: heavy discharge + OVER_TEMP")
        _pump(app, 0.22)
        frames.append(_grab(window))

    view.shutdown()
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=220,
        loop=0,
        optimize=True,
    )
    print(f"saved {out} ({len(frames)} frames, {os.path.getsize(out) // 1024} KiB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
