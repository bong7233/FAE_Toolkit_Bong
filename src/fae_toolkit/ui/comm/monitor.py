"""TX/RX monitor: timestamped, HEX and/or ASCII, clearable, savable."""

from __future__ import annotations

import time

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from fae_toolkit.core.hexfmt import to_ascii, to_hex
from fae_toolkit.protocols.modbus import describe_frame
from fae_toolkit.ui.i18n import i18n, tr


class MonitorWidget(QGroupBox):
    """A reusable communication monitor (one per tab)."""

    def __init__(self) -> None:
        super().__init__()
        self._build()
        i18n.subscribe(self.retranslate)
        self.retranslate()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        options = QHBoxLayout()
        self.cb_hex = QCheckBox()
        self.cb_hex.setChecked(True)
        self.cb_ascii = QCheckBox()
        self.cb_ascii.setChecked(True)
        self.cb_ts = QCheckBox()
        self.cb_ts.setChecked(True)
        self.cb_autoscroll = QCheckBox()
        self.cb_autoscroll.setChecked(True)
        self.cb_modbus = QCheckBox()
        self.cb_modbus.setChecked(False)
        self.btn_clear = QPushButton()
        self.btn_clear.clicked.connect(self._clear)
        self.btn_save = QPushButton()
        self.btn_save.clicked.connect(self._save)
        for w in (self.cb_hex, self.cb_ascii, self.cb_ts, self.cb_autoscroll, self.cb_modbus):
            options.addWidget(w)
        options.addStretch(1)
        options.addWidget(self.btn_clear)
        options.addWidget(self.btn_save)

        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setMaximumBlockCount(5000)
        self.view.setFont(QFont("monospace"))

        layout.addLayout(options)
        layout.addWidget(self.view)

    def append(self, direction: str, data: bytes) -> None:
        """Append a TX/RX entry formatted per the current options."""
        parts: list[str] = []
        if self.cb_ts.isChecked():
            parts.append(time.strftime("%H:%M:%S"))
        parts.append(f"{direction:>2}")
        if self.cb_hex.isChecked():
            parts.append(to_hex(data))
        if self.cb_ascii.isChecked():
            parts.append(f"| {to_ascii(data)}")
        self.view.appendPlainText("  ".join(parts))
        if self.cb_modbus.isChecked():
            decoded = describe_frame(data, response=(direction.strip() == "RX"))
            if decoded:
                self.view.appendPlainText(f"      └─ {decoded}")
        if self.cb_autoscroll.isChecked():
            self.view.ensureCursorVisible()

    def log(self, message: str) -> None:
        self.view.appendPlainText(f"-- {message}")

    def append_text(self, text: str) -> None:
        """Append a pre-formatted line (used by the CAN tab for frames)."""
        if self.cb_ts.isChecked():
            text = f"{time.strftime('%H:%M:%S')}  {text}"
        self.view.appendPlainText(text)
        if self.cb_autoscroll.isChecked():
            self.view.ensureCursorVisible()

    def _clear(self) -> None:
        self.view.clear()

    def _save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, tr("btn.save"), "comm_log.txt", "Text (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self.view.toPlainText())

    def retranslate(self) -> None:
        self.setTitle(tr("group.monitor"))
        self.cb_hex.setText(tr("monitor.show_hex"))
        self.cb_ascii.setText(tr("monitor.show_ascii"))
        self.cb_ts.setText(tr("monitor.timestamp"))
        self.cb_autoscroll.setText(tr("monitor.autoscroll"))
        self.cb_modbus.setText(tr("monitor.decode_modbus"))
        self.btn_clear.setText(tr("btn.clear"))
        self.btn_save.setText(tr("btn.save"))
