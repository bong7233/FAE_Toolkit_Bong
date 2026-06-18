"""CAN communication tab: configure a bus, send frames (ID + data), watch RX."""

from __future__ import annotations

import can
from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from fae_toolkit.core.hexfmt import parse_hex, to_hex
from fae_toolkit.ui.comm.monitor import MonitorWidget
from fae_toolkit.ui.i18n import i18n, tr


class _CanReader(QObject):
    received = Signal(int, bytes)
    error = Signal(str)

    def __init__(self, bus: can.BusABC, timeout: float = 0.2) -> None:
        super().__init__()
        self._bus = bus
        self._timeout = timeout
        self._running = False

    @Slot()
    def start(self) -> None:
        self._running = True
        while self._running:
            try:
                msg = self._bus.recv(timeout=self._timeout)
            except Exception as exc:
                if self._running:
                    self.error.emit(f"{type(exc).__name__}: {exc}")
                return
            if msg is not None:
                self.received.emit(msg.arbitration_id, bytes(msg.data))

    def stop(self) -> None:
        self._running = False


class CanTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._bus: can.BusABC | None = None
        self._thread: QThread | None = None
        self._reader: _CanReader | None = None
        self._connected = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._send)
        self._build()
        i18n.subscribe(self.retranslate)
        self.retranslate()
        self._update_controls()

    def _build(self) -> None:
        root = QHBoxLayout(self)
        left = QVBoxLayout()

        self.conn_box = QGroupBox()
        form = QFormLayout(self.conn_box)
        self.iface = QComboBox()
        self.iface.addItems(["virtual", "socketcan", "pcan", "kvaser"])
        self.iface.setEditable(True)
        self.channel = QLineEdit("fae_gui")
        self.bitrate = QSpinBox()
        self.bitrate.setRange(10000, 1000000)
        self.bitrate.setSingleStep(50000)
        self.bitrate.setValue(500000)
        self.row_iface = form.addRow(tr("field.interface"), self.iface)
        form.addRow(tr("field.channel"), self.channel)
        form.addRow(tr("field.bitrate"), self.bitrate)
        self._form = form
        left.addWidget(self.conn_box)

        self.status = QLabel()
        self._set_status("status.disconnected", "#777")
        left.addWidget(self.status)
        self.connect_btn = QPushButton()
        self.connect_btn.clicked.connect(self._toggle)
        left.addWidget(self.connect_btn)

        self.send_box = QGroupBox()
        send_form = QFormLayout(self.send_box)
        self.can_id = QLineEdit("180")
        self.data = QLineEdit("01 02 03 04")
        send_row = QWidget()
        send_layout = QHBoxLayout(send_row)
        send_layout.setContentsMargins(0, 0, 0, 0)
        self.send_btn = QPushButton()
        self.send_btn.clicked.connect(self._send)
        self.periodic = QSpinBox()
        self.periodic.setRange(0, 60000)
        self.periodic.setValue(0)
        self.periodic.setSpecialValueText("once")
        self.periodic.setSuffix(" ms")
        self.periodic_btn = QPushButton("⟳")
        self.periodic_btn.setCheckable(True)
        self.periodic_btn.toggled.connect(self._toggle_periodic)
        send_layout.addWidget(self.send_btn)
        send_layout.addWidget(self.periodic)
        send_layout.addWidget(self.periodic_btn)
        self._id_label_key = "field.can_id"
        send_form.addRow(tr("field.can_id"), self.can_id)
        send_form.addRow("Data (hex)", self.data)
        send_form.addRow(send_row)
        self._send_form = send_form
        left.addWidget(self.send_box)
        left.addStretch(1)
        root.addLayout(left, stretch=0)

        self.monitor = MonitorWidget()
        root.addWidget(self.monitor, stretch=1)

    # --- connection ------------------------------------------------------- #
    def _toggle(self) -> None:
        self._disconnect() if self._connected else self._connect()

    def _connect(self) -> None:
        iface = self.iface.currentText().strip() or "virtual"
        channel = self.channel.text().strip() or "fae_gui"
        kwargs: dict = {}
        if iface != "virtual":
            kwargs["bitrate"] = self.bitrate.value()
        try:
            self._bus = can.Bus(interface=iface, channel=channel, **kwargs)
        except Exception as exc:
            self.monitor.log(f"connect failed: {type(exc).__name__}: {exc}")
            self._set_status("status.disconnected", "#c0392b")
            return

        self._thread = QThread(self)
        self._reader = _CanReader(self._bus)
        self._reader.moveToThread(self._thread)
        self._thread.started.connect(self._reader.start)
        self._reader.received.connect(self._on_rx)
        self._reader.error.connect(self._on_error)
        self._thread.start()

        self._connected = True
        self._set_status("status.connected", "#27ae60")
        self.monitor.log(f"connected to {iface}:{channel}")
        self._update_controls()

    def _disconnect(self) -> None:
        self.periodic_btn.setChecked(False)
        if self._reader is not None:
            self._reader.stop()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
        if self._bus is not None:
            try:
                self._bus.shutdown()
            except Exception:
                pass
        self._bus = None
        self._reader = None
        self._thread = None
        self._connected = False
        self._set_status("status.disconnected", "#777")
        self.monitor.log("disconnected")
        self._update_controls()

    @Slot(int, bytes)
    def _on_rx(self, can_id: int, data: bytes) -> None:
        self.monitor.append_text(f"RX  ID=0x{can_id:X}  [{len(data)}]  {to_hex(data)}")

    @Slot(str)
    def _on_error(self, message: str) -> None:
        self.monitor.log(f"error: {message}")
        self._disconnect()

    def _send(self) -> None:
        if not self._connected or self._bus is None:
            self.monitor.log("not connected")
            return
        try:
            can_id = int(self.can_id.text().strip(), 16)
            data = parse_hex(self.data.text())
        except ValueError as exc:
            self.monitor.log(f"send error: {exc}")
            return
        try:
            self._bus.send(can.Message(arbitration_id=can_id, data=data, is_extended_id=False))
            self.monitor.append_text(f"TX  ID=0x{can_id:X}  [{len(data)}]  {to_hex(data)}")
        except Exception as exc:
            self.monitor.log(f"send failed: {exc}")

    def _toggle_periodic(self, on: bool) -> None:
        if on and self.periodic.value() > 0:
            self._timer.start(self.periodic.value())
        else:
            self._timer.stop()

    # --- helpers ---------------------------------------------------------- #
    def _set_status(self, key: str, color: str) -> None:
        self._status_key = key
        self.status.setText(tr(key))
        self.status.setStyleSheet(
            f"background:{color}; color:white; font-weight:bold; border-radius:4px; padding:4px;"
        )

    def _update_controls(self) -> None:
        self.connect_btn.setText(tr("btn.disconnect") if self._connected else tr("btn.connect"))
        for w in (self.iface, self.channel, self.bitrate):
            w.setEnabled(not self._connected)
        self.send_btn.setEnabled(self._connected)
        self.periodic_btn.setEnabled(self._connected)

    def retranslate(self) -> None:
        self.conn_box.setTitle(tr("group.connection"))
        self.send_box.setTitle(tr("group.send"))
        self.send_btn.setText(tr("btn.send"))
        if hasattr(self, "_status_key"):
            self.status.setText(tr(self._status_key))
        self._update_controls()

    def shutdown(self) -> None:
        if self._connected:
            self._disconnect()
