"""Render the Comm Tester and TeachingManager to PNGs (offscreen Qt).

QT_QPA_PLATFORM=offscreen python docs/capture_screenshot.py
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from fae_toolkit.teaching_manager.main_window import MainWindow as TeachingWindow  # noqa: E402
from fae_toolkit.ui.main_window import MainWindow  # noqa: E402


def _pump(app: QApplication, seconds: float) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.02)


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _start_echo_server(port: int) -> socket.socket:
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
        conn.settimeout(5)
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


def _save(window, out: str) -> None:
    ok = window.grab().save(out, "PNG")
    print(f"saved={ok} -> {out}")


def main() -> int:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.resize(1100, 680)
    window.show()
    tabs = window._tabs

    # Serial tab: show configured frame sender with a Modbus preset.
    tabs.setCurrentIndex(0)
    window.serial_tab.sender.format_combo.setCurrentText("HEX")
    window.serial_tab.sender.input.setText("01 03 00 00 00 0A")
    window.serial_tab.sender.cb_crc.setChecked(True)
    _pump(app, 0.3)
    _save(window, "docs/screenshot_comm_serial.png")

    # TCP tab: live loopback against a local echo server.
    port = _free_port()
    srv = _start_echo_server(port)
    tabs.setCurrentIndex(1)
    tcp = window.tcp_tab
    tcp._panel.mode.setCurrentIndex(0)  # client
    tcp._panel.host.setText("127.0.0.1")
    tcp._panel.port.setValue(port)
    tcp._connect()
    tcp.monitor.cb_modbus.setChecked(True)  # show the Modbus frame decoder
    _pump(app, 0.5)
    for payload, crc in (
        ("01 03 00 00 00 0A", True),
        ("DE AD BE EF", False),
        ("48 65 6C 6C 6F", False),
    ):
        tcp.sender.input.setText(payload)
        tcp.sender.cb_crc.setChecked(crc)
        tcp.sender._emit()
        _pump(app, 0.4)
    _save(window, "docs/screenshot_comm_tcp.png")
    tcp.shutdown()
    srv.close()

    # CAN tab: configuration view.
    tabs.setCurrentIndex(3)
    _pump(app, 0.2)
    _save(window, "docs/screenshot_comm_can.png")
    window.close()

    # TeachingManager (separate app).
    tm = TeachingWindow()
    tm.resize(1100, 680)
    tm.show()
    tm.view.table.selectRow(4)
    tm.view._validate()
    _pump(app, 0.4)
    _save(tm, "docs/screenshot_teaching.png")
    tm.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
