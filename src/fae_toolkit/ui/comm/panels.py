"""Per-transport connection parameter panels (Serial / TCP / UDP).

Each panel builds a real :class:`Transport` from its fields; ``build_transport``
raises if parameters are invalid, and opening it fails if the device/host is
unavailable — no fabricated connections.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

from fae_toolkit.core.net import TcpClientTransport, TcpServerTransport, UdpTransport
from fae_toolkit.core.transport import SerialTransport, Transport
from fae_toolkit.ui.i18n import i18n, tr


class ConnectionPanel(QGroupBox):
    """Base class: a titled form that yields a transport."""

    def __init__(self) -> None:
        super().__init__()
        self._form = QFormLayout(self)
        self._rows: list[tuple[str, QWidget]] = []
        i18n.subscribe(self.retranslate)

    def add_row(self, key: str, widget: QWidget) -> QWidget:
        self._form.addRow(tr(key), widget)
        self._rows.append((key, widget))
        return widget

    def build_transport(self) -> Transport:  # pragma: no cover - overridden
        raise NotImplementedError

    def set_params_enabled(self, enabled: bool) -> None:
        for _key, widget in self._rows:
            widget.setEnabled(enabled)

    def retranslate(self) -> None:
        self.setTitle(tr("group.connection"))
        for i, (key, _widget) in enumerate(self._rows):
            label = self._form.itemAt(i, QFormLayout.ItemRole.LabelRole)
            if label is not None and label.widget() is not None:
                label.widget().setText(tr(key))


class SerialPanel(ConnectionPanel):
    def __init__(self) -> None:
        super().__init__()
        port_row = QWidget()
        port_layout = QHBoxLayout(port_row)
        port_layout.setContentsMargins(0, 0, 0, 0)
        self.port = QComboBox()
        self.port.setEditable(True)
        self.refresh_btn = QPushButton()
        self.refresh_btn.clicked.connect(self.refresh_ports)
        port_layout.addWidget(self.port, stretch=1)
        port_layout.addWidget(self.refresh_btn)

        self.baud = QComboBox()
        self.baud.setEditable(True)
        self.baud.addItems(["9600", "19200", "38400", "57600", "115200", "230400"])
        self.baud.setCurrentText("9600")
        self.databits = QComboBox()
        self.databits.addItems(["8", "7", "6", "5"])
        self.parity = QComboBox()
        self.parity.addItems(["N", "E", "O", "M", "S"])
        self.stopbits = QComboBox()
        self.stopbits.addItems(["1", "1.5", "2"])

        self.add_row("field.port", port_row)
        self.add_row("field.baud", self.baud)
        self.add_row("field.databits", self.databits)
        self.add_row("field.parity", self.parity)
        self.add_row("field.stopbits", self.stopbits)
        self.refresh_ports()
        self.retranslate()

    def refresh_ports(self) -> None:
        current = self.port.currentText()
        self.port.clear()
        try:
            from serial.tools import list_ports

            for info in list_ports.comports():
                self.port.addItem(info.device)
        except Exception:
            pass
        if current:
            self.port.setCurrentText(current)

    def build_transport(self) -> Transport:
        port = self.port.currentText().strip()
        if not port:
            raise ValueError("no serial port selected")
        return SerialTransport(
            port,
            baudrate=int(self.baud.currentText()),
            bytesize=int(self.databits.currentText()),
            parity=self.parity.currentText(),
            stopbits=float(self.stopbits.currentText()),
        )

    def retranslate(self) -> None:
        super().retranslate()
        if hasattr(self, "refresh_btn"):
            self.refresh_btn.setText(tr("btn.refresh"))


class TcpPanel(ConnectionPanel):
    def __init__(self) -> None:
        super().__init__()
        self.mode = QComboBox()
        self.mode.addItems([tr("mode.client"), tr("mode.server")])
        self.host = QLineEdit("127.0.0.1")
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(502)  # Modbus-TCP default
        self.add_row("field.mode", self.mode)
        self.add_row("field.host", self.host)
        self.add_row("field.tcp_port", self.port)
        self.retranslate()

    def build_transport(self) -> Transport:
        port = self.port.value()
        if self.mode.currentIndex() == 0:  # client
            host = self.host.text().strip() or "127.0.0.1"
            return TcpClientTransport(host, port)
        return TcpServerTransport(port, host="0.0.0.0")

    def retranslate(self) -> None:
        super().retranslate()
        idx = self.mode.currentIndex() if hasattr(self, "mode") else 0
        if hasattr(self, "mode"):
            self.mode.blockSignals(True)
            self.mode.clear()
            self.mode.addItems([tr("mode.client"), tr("mode.server")])
            self.mode.setCurrentIndex(idx)
            self.mode.blockSignals(False)


class UdpPanel(ConnectionPanel):
    def __init__(self) -> None:
        super().__init__()
        self.remote_host = QLineEdit("127.0.0.1")
        self.remote_port = QSpinBox()
        self.remote_port.setRange(1, 65535)
        self.remote_port.setValue(5005)
        self.local_port = QSpinBox()
        self.local_port.setRange(0, 65535)
        self.local_port.setValue(5006)
        self.add_row("field.remote_host", self.remote_host)
        self.add_row("field.remote_port", self.remote_port)
        self.add_row("field.local_port", self.local_port)
        self.retranslate()

    def build_transport(self) -> Transport:
        host = self.remote_host.text().strip() or "127.0.0.1"
        return UdpTransport(host, self.remote_port.value(), local_port=self.local_port.value())
