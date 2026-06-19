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

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from fae_toolkit.teaching import BackgroundImage, TeachingStatus  # noqa: E402
from fae_toolkit.teaching_manager.main_window import MainWindow as TeachingWindow  # noqa: E402
from fae_toolkit.ui.main_window import MainWindow  # noqa: E402


def _make_floorplan(path: str, w: int = 380, h: int = 760) -> None:
    """Draw a simple plant floor-plan PNG to demo the CAD background feature."""
    img = QImage(w, h, QImage.Format.Format_RGBA8888)
    img.fill(QColor("#ffffff"))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#34495e"), 5))  # outer wall
    p.drawRect(10, 10, w - 20, h - 20)
    p.setPen(QPen(QColor("#b0b8c0"), 2, Qt.PenStyle.DashLine))  # main aisle
    p.drawLine(w // 2, 24, w // 2, h - 24)
    p.setFont(QFont("sans", 13))
    for x, y, bw, bh, label, col in (
        (40, 60, 120, 90, "STATION A", "#2980b9"),
        (w - 170, 300, 130, 110, "STATION B", "#16a085"),
        (40, h - 150, 110, 80, "CHARGER", "#8e44ad"),
    ):
        p.setPen(QPen(QColor(col), 3))
        p.setBrush(QColor(col).lighter(170))
        p.drawRect(x, y, bw, bh)
        p.setPen(QColor("#2c3e50"))
        p.drawText(x + 8, y + 22, label)
    p.end()
    img.save(path, "PNG")


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

    # TeachingManager (separate app): CAD background + status colours + types.
    tm = TeachingWindow()
    tm.resize(1180, 720)
    tm.show()
    floor = "docs/sample_floorplan.png"
    _make_floorplan(floor)
    view = tm.view
    view._project.background = BackgroundImage(path=floor, x=-400, y=-400, scale=10.0, opacity=0.5)
    view._project.points[5].status = TeachingStatus.ALARM  # showcase an alarm marker
    view._reload()
    view.table.selectRow(4)
    _pump(app, 0.4)
    _save(tm, "docs/screenshot_teaching.png")
    # Second shot: the equipment-types editor (custom colour/shape per type).
    tm.view.tabs.setCurrentIndex(1)
    _pump(app, 0.3)
    _save(tm, "docs/screenshot_teaching_types.png")
    tm.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
