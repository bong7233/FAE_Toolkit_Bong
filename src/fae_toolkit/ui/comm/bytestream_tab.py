"""A byte-stream communication tab (shared by Serial / TCP / UDP).

Composes a connection panel + frame sender + monitor, manages a real
connection and a background read thread, and wires TX/RX to the monitor.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Slot
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from fae_toolkit.core.transport import Transport
from fae_toolkit.ui.comm.monitor import MonitorWidget
from fae_toolkit.ui.comm.panels import ConnectionPanel
from fae_toolkit.ui.comm.reader import RxReader
from fae_toolkit.ui.comm.sender import FrameSenderWidget
from fae_toolkit.ui.i18n import i18n, tr


class ByteStreamTab(QWidget):
    def __init__(self, panel: ConnectionPanel) -> None:
        super().__init__()
        self._panel = panel
        self._transport: Transport | None = None
        self._thread: QThread | None = None
        self._reader: RxReader | None = None
        self._connected = False

        self._build()
        i18n.subscribe(self.retranslate)
        self.retranslate()
        self._update_controls()

    def _build(self) -> None:
        root = QHBoxLayout(self)
        left = QVBoxLayout()
        left.addWidget(self._panel)
        self.status = QLabel()
        self.status.setMinimumHeight(28)
        self._set_status("status.disconnected", "#777")
        left.addWidget(self.status)
        self.connect_btn = QPushButton()
        self.connect_btn.clicked.connect(self._toggle)
        left.addWidget(self.connect_btn)
        self.sender = FrameSenderWidget()
        self.sender.send_requested.connect(self._send)
        self.sender.error.connect(lambda m: self.monitor.log(f"send error: {m}"))
        left.addWidget(self.sender)
        left.addStretch(1)
        root.addLayout(left, stretch=0)

        self.monitor = MonitorWidget()
        root.addWidget(self.monitor, stretch=1)

    # --- connection ------------------------------------------------------- #
    def _toggle(self) -> None:
        self._disconnect() if self._connected else self._connect()

    def _connect(self) -> None:
        try:
            transport = self._panel.build_transport()
            transport.open()
        except Exception as exc:
            self.monitor.log(f"connect failed: {type(exc).__name__}: {exc}")
            self._set_status("status.disconnected", "#c0392b")
            return
        self._transport = transport

        self._thread = QThread(self)
        self._reader = RxReader(transport)
        self._reader.moveToThread(self._thread)
        self._thread.started.connect(self._reader.start)
        self._reader.received.connect(self._on_rx)
        self._reader.error.connect(self._on_error)
        self._thread.start()

        self._connected = True
        listening = getattr(transport, "has_client", True) is False
        self._set_status("status.listening" if listening else "status.connected", "#27ae60")
        self.monitor.log("connected")
        self._update_controls()

    def _disconnect(self) -> None:
        if self._reader is not None:
            self._reader.stop()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
        if self._transport is not None:
            try:
                self._transport.close()
            except Exception:
                pass
        self._transport = None
        self._reader = None
        self._thread = None
        self._connected = False
        self._set_status("status.disconnected", "#777")
        self.monitor.log("disconnected")
        self._update_controls()

    @Slot(bytes)
    def _on_rx(self, data: bytes) -> None:
        self.monitor.append("RX", data)

    @Slot(str)
    def _on_error(self, message: str) -> None:
        self.monitor.log(f"error: {message}")
        self._disconnect()

    def _send(self, data: bytes) -> None:
        if not self._connected or self._transport is None:
            self.monitor.log("not connected")
            return
        try:
            self._transport.write(data)
            self.monitor.append("TX", data)
        except Exception as exc:
            self.monitor.log(f"write failed: {exc}")
            self._disconnect()

    # --- helpers ---------------------------------------------------------- #
    def _set_status(self, key: str, color: str) -> None:
        self._status_key = key
        self.status.setText(tr(key))
        self.status.setStyleSheet(
            f"background:{color}; color:white; font-weight:bold; border-radius:4px; padding:4px;"
        )

    def _update_controls(self) -> None:
        self.connect_btn.setText(tr("btn.disconnect") if self._connected else tr("btn.connect"))
        self._panel.set_params_enabled(not self._connected)
        self.sender.set_enabled(self._connected)

    def retranslate(self) -> None:
        if hasattr(self, "_status_key"):
            self.status.setText(tr(self._status_key))
        self._update_controls()

    def shutdown(self) -> None:
        if self._connected:
            self._disconnect()
