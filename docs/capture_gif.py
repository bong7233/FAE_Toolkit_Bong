"""Animated GIF of the Comm Tester over a live TCP loopback (offscreen Qt).

QT_QPA_PLATFORM=offscreen python docs/capture_gif.py
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image  # noqa: E402
from PySide6.QtGui import QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from fae_toolkit.ui.main_window import MainWindow  # noqa: E402

_FRAME_W = 640


def _grab(window) -> Image.Image:
    qimg = window.grab().toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    img = Image.frombytes("RGBA", (qimg.width(), qimg.height()), bytes(qimg.constBits()))
    ratio = _FRAME_W / img.width
    return img.resize((_FRAME_W, int(img.height * ratio))).convert("RGB")


def _pump(app, seconds: float) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.02)


def _echo_server(port: int) -> socket.socket:
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(1)
    srv.settimeout(5)

    def run() -> None:
        try:
            conn, _ = srv.accept()
        except OSError:
            return
        while True:
            try:
                data = conn.recv(4096)
            except OSError:
                break
            if not data:
                break
            conn.sendall(data)

    threading.Thread(target=run, daemon=True).start()
    return srv


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else "docs/demo_comm.gif"
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.resize(1100, 680)
    window.show()
    window._tabs.setCurrentIndex(1)  # TCP

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    srv = _echo_server(port)

    tcp = window.tcp_tab
    tcp._panel.host.setText("127.0.0.1")
    tcp._panel.port.setValue(port)
    tcp._connect()
    tcp.monitor.cb_modbus.setChecked(True)  # annotate frames with the Modbus decoder
    _pump(app, 0.4)

    payloads = [
        ("01 03 00 00 00 0A", True),
        ("DE AD BE EF", False),
        ("48 65 6C 6C 6F", False),
        ("01 06 00 00 00 01", True),
        ("FF 00 FF 00", False),
    ]
    frames: list[Image.Image] = []
    for i in range(20):
        if i % 2 == 0:
            text, crc = payloads[(i // 2) % len(payloads)]
            tcp.sender.input.setText(text)
            tcp.sender.cb_crc.setChecked(crc)
            tcp.sender._emit()
        _pump(app, 0.25)
        frames.append(_grab(window))

    tcp.shutdown()
    srv.close()
    frames[0].save(
        out, save_all=True, append_images=frames[1:], duration=260, loop=0, optimize=True
    )
    print(f"saved {out} ({len(frames)} frames, {os.path.getsize(out) // 1024} KiB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
