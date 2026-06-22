"""Offscreen smoke tests for the Comm Tester and TeachingManager GUIs.

Skipped when PySide6 is not installed. Runs under the Qt 'offscreen' platform.
"""

import os
import socket
import time

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from fae_toolkit.core.net import TcpClientTransport  # noqa: E402
from fae_toolkit.ui.i18n import i18n  # noqa: E402
from fae_toolkit.ui.main_window import MainWindow  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _pump_until(qapp, predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.02)


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_comm_window_builds_and_language_toggle(qapp):
    window = MainWindow()
    assert window._tabs.count() == 4
    try:
        i18n.set_language("ko")
        assert "통신" in window.windowTitle()
        i18n.set_language("en")
        assert "Comm Tester" in window.windowTitle()
    finally:
        i18n.set_language("en")
        window.close()


def test_tcp_tab_receives_over_loopback(qapp):
    window = MainWindow()
    tab = window.tcp_tab
    port = _free_port()
    tab._panel.mode.setCurrentIndex(1)  # server (listen)
    tab._panel.port.setValue(port)
    tab._connect()
    assert tab._connected

    client = TcpClientTransport("127.0.0.1", port)
    opened = False
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        try:
            client.open()
            opened = True
            break
        except OSError:
            qapp.processEvents()
            time.sleep(0.05)
    assert opened
    client.write(b"\xaa\xbb\xcc")

    _pump_until(qapp, lambda: "AA BB CC" in tab.monitor.view.toPlainText())
    assert "AA BB CC" in tab.monitor.view.toPlainText()

    client.close()
    tab.shutdown()
    window.close()


def test_send_builds_crc_frame(qapp):
    # The frame sender builds the correct Modbus-CRC frame from hex input.
    window = MainWindow()
    sender = window.serial_tab.sender
    sender.format_combo.setCurrentText("HEX")
    sender.input.setText("01 03 00 00 00 0A")
    sender.cb_crc.setChecked(True)
    assert sender.build_bytes().hex() == "01030000000ac5cd"
    window.close()


def test_macro_panel_save_apply_delete(qapp, tmp_path):
    from fae_toolkit.ui.comm.macros_panel import MacroPanel
    from fae_toolkit.ui.comm.sender import FrameSenderWidget

    sender = FrameSenderWidget()
    panel = MacroPanel(sender, store_path=tmp_path / "m.json")

    sender.format_combo.setCurrentText("HEX")
    sender.input.setText("01 03 00 00 00 0A")
    sender.cb_crc.setChecked(True)
    panel._save_named("MakerX read", group="MakerX")

    # Reload from a fresh panel to prove it persisted to disk.
    panel2 = MacroPanel(FrameSenderWidget(), store_path=tmp_path / "m.json")
    assert "MakerX read" in panel2._store.names()
    assert "MakerX" in panel2._store.groups()

    # Clear the sender, then load the saved macro back into it.
    sender.input.clear()
    sender.cb_crc.setChecked(False)
    assert panel._apply_name("MakerX read") is True
    assert sender.input.text() == "01 03 00 00 00 0A"
    assert sender.cb_crc.isChecked() is True

    panel._store.remove("MakerX read")
    panel._persist()
    panel3 = MacroPanel(FrameSenderWidget(), store_path=tmp_path / "m.json")
    assert "MakerX read" not in panel3._store.names()


def test_monitor_modbus_decode_annotates_rx(qapp):
    from fae_toolkit.protocols import modbus
    from fae_toolkit.ui.comm.monitor import MonitorWidget

    monitor = MonitorWidget()
    monitor.cb_modbus.setChecked(True)
    response = modbus.process_request(
        modbus.build_read_holding_registers(unit=1, start=0, count=2),
        unit_id=1,
        read_holding=lambda s, c: [111, 222],
    )
    monitor.append("RX", response)
    text = monitor.view.toPlainText()
    assert "RSP" in text
    assert "[111, 222]" in text


def test_teaching_manager_window(qapp):
    from fae_toolkit.teaching_manager.main_window import MainWindow as TeachingWindow

    window = TeachingWindow()
    assert window.view.table.rowCount() == 6
    window.view._validate()
    assert "OK" in window.view.log_view.toPlainText()
    window.close()


def test_teaching_add_type_button_adds_styleable_entry(qapp, monkeypatch):
    # Regression: the "Add type" button used to be a no-op (broken existence
    # check), so a new equipment type could never be created or styled.
    from fae_toolkit.teaching_manager import view as tmview

    v = tmview.TeachingView()
    before = len(v._project.styles)
    monkeypatch.setattr(tmview.QInputDialog, "getText", lambda *a, **k: ("DOCK", True))
    v._add_type()
    assert v._project.has_style("DOCK")
    assert len(v._project.styles) == before + 1
    v._add_type()  # same name again must not duplicate
    assert len(v._project.styles) == before + 1
    v.close()


def test_teaching_typed_type_registers_style_on_commit(qapp):
    # Typing a brand-new type into a point row updates the point live and, once
    # editing is committed, registers a styleable entry for it.
    from fae_toolkit.teaching_manager.view import TeachingView

    v = TeachingView()
    combo = v.table.cellWidget(0, 2)  # row 0 "type" combo
    combo.setCurrentText("AGV_PARK")
    assert v._project.points[0].type == "AGV_PARK"
    assert not v._project.has_style("AGV_PARK")  # not yet, still editing
    v._commit_type(combo)
    assert v._project.has_style("AGV_PARK")
    v.close()
