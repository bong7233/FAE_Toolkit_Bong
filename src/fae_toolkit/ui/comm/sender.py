"""Frame sender: HEX/ASCII entry, optional Modbus CRC/CRLF, one-shot or periodic."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from fae_toolkit.core.crc import append_crc
from fae_toolkit.core.hexfmt import parse_hex
from fae_toolkit.ui.i18n import i18n, tr

# (key, hex payload to insert, enable-crc) presets reuse the protocol knowledge.
_PRESETS = {
    "preset.modbus_read": ("01 03 00 00 00 0A", True),
}


class FrameSenderWidget(QGroupBox):
    send_requested = Signal(bytes)
    error = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._emit)
        self._build()
        i18n.subscribe(self.retranslate)
        self.retranslate()

    def _build(self) -> None:
        layout = QVBoxLayout(self)

        row_input = QHBoxLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(["HEX", "ASCII"])
        self.format_combo.currentIndexChanged.connect(self._update_placeholder)
        self.input = QLineEdit()
        self.send_btn = QPushButton()
        self.send_btn.clicked.connect(self._emit)
        row_input.addWidget(self.format_combo)
        row_input.addWidget(self.input, stretch=1)
        row_input.addWidget(self.send_btn)

        row_opts = QHBoxLayout()
        self.cb_crc = QCheckBox()
        self.cb_crlf = QCheckBox()
        self.cb_periodic = QCheckBox()
        self.cb_periodic.toggled.connect(self._toggle_periodic)
        self.interval = QSpinBox()
        self.interval.setRange(20, 60000)
        self.interval.setValue(1000)
        self.interval.setSingleStep(100)
        row_opts.addWidget(self.cb_crc)
        row_opts.addWidget(self.cb_crlf)
        row_opts.addStretch(1)
        row_opts.addWidget(self.cb_periodic)
        row_opts.addWidget(self.interval)

        row_preset = QHBoxLayout()
        self.preset_combo = QComboBox()
        self.preset_label_btn = QPushButton()
        self.preset_label_btn.clicked.connect(self._apply_preset)
        row_preset.addWidget(self.preset_combo, stretch=1)
        row_preset.addWidget(self.preset_label_btn)

        layout.addLayout(row_input)
        layout.addLayout(row_opts)
        layout.addLayout(row_preset)

    # --- behaviour -------------------------------------------------------- #
    def build_bytes(self) -> bytes:
        text = self.input.text()
        if self.format_combo.currentText() == "HEX":
            payload = parse_hex(text)
        else:
            payload = text.encode("utf-8", errors="replace")
        if self.cb_crc.isChecked():
            payload = append_crc(payload)
        if self.cb_crlf.isChecked():
            payload = payload + b"\r\n"
        return payload

    def _emit(self) -> None:
        try:
            payload = self.build_bytes()
        except ValueError as exc:
            self.error.emit(str(exc))
            return
        if payload:
            self.send_requested.emit(payload)

    def _toggle_periodic(self, on: bool) -> None:
        if on:
            self._timer.start(self.interval.value())
        else:
            self._timer.stop()

    def _apply_preset(self) -> None:
        key = self.preset_combo.currentData()
        if key in _PRESETS:
            payload, crc = _PRESETS[key]
            self.format_combo.setCurrentText("HEX")
            self.input.setText(payload)
            self.cb_crc.setChecked(crc)

    def set_enabled(self, enabled: bool) -> None:
        self.send_btn.setEnabled(enabled)
        if not enabled and self.cb_periodic.isChecked():
            self.cb_periodic.setChecked(False)

    def _update_placeholder(self) -> None:
        if self.format_combo.currentText() == "HEX":
            self.input.setPlaceholderText(tr("send.placeholder_hex"))
        else:
            self.input.setPlaceholderText(tr("send.placeholder_ascii"))

    def retranslate(self) -> None:
        self.setTitle(tr("group.send"))
        self.send_btn.setText(tr("btn.send"))
        self.cb_crc.setText(tr("send.append_crc"))
        self.cb_crlf.setText(tr("send.append_newline"))
        self.cb_periodic.setText(tr("send.periodic"))
        self.interval.setSuffix(" " + tr("send.ms"))
        self.preset_label_btn.setText(tr("preset.apply"))
        current = self.preset_combo.currentData()
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem(tr("preset.none"), None)
        for key in _PRESETS:
            self.preset_combo.addItem(tr(key), key)
        idx = self.preset_combo.findData(current)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        self.preset_combo.blockSignals(False)
        self._update_placeholder()
