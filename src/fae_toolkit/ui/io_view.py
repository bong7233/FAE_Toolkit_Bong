"""Remote-IO / PIO test panel.

Shows digital inputs as indicators, digital outputs as toggles (with a
controller-driven light tower), and analog inputs as live values. Demonstrates
interlock enforcement: motion outputs are refused while the E-stop is tripped.
"""

from __future__ import annotations

import threading
import time

from PySide6.QtCore import QMetaObject, Qt, QThread, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from fae_toolkit.core.transport import SerialTransport, create_loopback_pair
from fae_toolkit.protocols.io import IoClient, io_map
from fae_toolkit.protocols.io.model import IoSnapshot
from fae_toolkit.protocols.modbus import ModbusError
from fae_toolkit.sim.io import IoSimulator
from fae_toolkit.ui.worker import PollWorker

SIM_LABEL = "Simulator (no hardware)"
# Outputs the operator can drive directly (the rest are the light tower).
_OPERATOR_OUTPUTS = (
    io_map.DO_VALID,
    io_map.DO_LOAD_CLAMP,
    io_map.DO_LIFT_UP,
    io_map.DO_LIFT_DOWN,
    io_map.DO_CONVEYOR,
    io_map.DO_BUZZER,
)
_ON_STYLE = "border-radius:7px; padding:3px; background:#27ae60; color:white;"
_OFF_STYLE = "border-radius:7px; padding:3px; background:#34495e; color:#aab;"
_RED_STYLE = "border-radius:7px; padding:3px; background:#c0392b; color:white;"
_AMBER_STYLE = "border-radius:7px; padding:3px; background:#e67e22; color:white;"


class IoView(QWidget):
    """Self-contained remote-IO test view."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sim: IoSimulator | None = None
        self._client: IoClient | None = None
        self._transport = None
        self._thread: QThread | None = None
        self._worker: PollWorker | None = None
        self._connected = False
        self._io_lock = threading.Lock()  # serialise transport access

        self._di_leds: dict[int, QLabel] = {}
        self._do_widgets: dict[int, QWidget] = {}
        self._ai_labels: dict[int, QLabel] = {}
        self._build_ui()
        self._update_controls()

    # --- UI construction -------------------------------------------------- #
    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        left = QVBoxLayout()
        left.addWidget(self._build_connection_group())
        left.addWidget(self._build_interlock_banner())
        left.addWidget(self._build_analog_group())
        left.addWidget(self._build_fault_group())
        left.addWidget(self._build_log_group(), stretch=1)
        root.addLayout(left, stretch=0)

        right = QVBoxLayout()
        right.addWidget(self._build_inputs_group())
        right.addWidget(self._build_outputs_group())
        root.addLayout(right, stretch=1)

    def _build_connection_group(self) -> QGroupBox:
        box = QGroupBox("연결 (Connection)")
        form = QFormLayout(box)
        self.port_combo = QComboBox()
        self.port_combo.addItem(SIM_LABEL)
        self.port_combo.setEditable(True)
        self.unit_spin = QSpinBox()
        self.unit_spin.setRange(1, 247)
        self.unit_spin.setValue(1)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(50, 5000)
        self.interval_spin.setSingleStep(50)
        self.interval_spin.setValue(300)
        self.interval_spin.setSuffix(" ms")
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._toggle_connection)
        form.addRow("Port", self.port_combo)
        form.addRow("Unit id", self.unit_spin)
        form.addRow("Poll", self.interval_spin)
        form.addRow(self.connect_btn)
        return box

    def _build_interlock_banner(self) -> QLabel:
        self.interlock_banner = QLabel("DISCONNECTED")
        self.interlock_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.interlock_banner.setMinimumHeight(34)
        self._set_banner("DISCONNECTED", "#777")
        return self.interlock_banner

    def _build_inputs_group(self) -> QGroupBox:
        box = QGroupBox("디지털 입력 (Discrete inputs · sensors / PIO)")
        grid = QGridLayout(box)
        for ch in range(io_map.DI_COUNT):
            led = QLabel(io_map.DI_NAMES[ch])
            led.setAlignment(Qt.AlignmentFlag.AlignCenter)
            led.setStyleSheet(_OFF_STYLE)
            grid.addWidget(led, ch // 4, ch % 4)
            self._di_leds[ch] = led
        return box

    def _build_outputs_group(self) -> QGroupBox:
        box = QGroupBox("디지털 출력 (Coils · actuators / light tower)")
        grid = QGridLayout(box)
        for ch in range(io_map.DO_COUNT):
            if ch in _OPERATOR_OUTPUTS:
                btn = QPushButton(io_map.DO_NAMES[ch])
                btn.setCheckable(True)
                btn.clicked.connect(lambda checked, c=ch: self._on_output_clicked(c, checked))
                grid.addWidget(btn, ch // 4, ch % 4)
                self._do_widgets[ch] = btn
            else:
                led = QLabel(io_map.DO_NAMES[ch])
                led.setAlignment(Qt.AlignmentFlag.AlignCenter)
                led.setStyleSheet(_OFF_STYLE)
                grid.addWidget(led, ch // 4, ch % 4)
                self._do_widgets[ch] = led
        return box

    def _build_analog_group(self) -> QGroupBox:
        box = QGroupBox("아날로그 입력 (Analog inputs)")
        form = QFormLayout(box)
        for ch in range(io_map.AI_COUNT):
            label = QLabel("—")
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            form.addRow(f"{io_map.AI_NAMES[ch]} ({io_map.AI_UNITS[ch]})", label)
            self._ai_labels[ch] = label
        return box

    def _build_fault_group(self) -> QGroupBox:
        box = QGroupBox("고장 주입 (Fault injection · simulator only)")
        grid = QGridLayout(box)
        self._fault_buttons: list[QPushButton] = []
        specs = [
            ("Trip E-STOP", lambda: self._sim and self._sim.trip_estop(True)),
            ("Block area", lambda: self._sim and self._sim.set_area_blocked(True)),
            ("Comm timeout", lambda: self._sim and self._sim.inject_comm_timeout(1)),
            ("CRC error", lambda: self._sim and self._sim.inject_crc_error()),
            ("Clear faults", self._clear_faults),
        ]
        for idx, (label, fn) in enumerate(specs):
            btn = QPushButton(label)
            btn.clicked.connect(fn)
            grid.addWidget(btn, idx // 2, idx % 2)
            self._fault_buttons.append(btn)
        return box

    def _build_log_group(self) -> QGroupBox:
        box = QGroupBox("이벤트 로그 (Event log)")
        layout = QVBoxLayout(box)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(500)
        layout.addWidget(self.log_view)
        return box

    # --- connection lifecycle -------------------------------------------- #
    def _toggle_connection(self) -> None:
        self._disconnect() if self._connected else self._connect()

    def _connect(self) -> None:
        target = self.port_combo.currentText().strip()
        try:
            if target == SIM_LABEL:
                app_end, dev_end = create_loopback_pair()
                self._sim = IoSimulator(dev_end, unit_id=self.unit_spin.value())
                self._sim.start()
                self._transport = app_end
            else:
                self._sim = None
                self._transport = SerialTransport(target)
                self._transport.open()
        except Exception as exc:
            self._log(f"connect failed: {exc}")
            self._cleanup_connection()
            return

        self._client = IoClient(self._transport, unit_id=self.unit_spin.value(), timeout=1.0)
        self._thread = QThread(self)
        self._worker = PollWorker(
            self._read_snapshot_locked, interval_ms=self.interval_spin.value()
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.start)
        self._thread.finished.connect(self._worker.deleteLater)
        self._worker.result.connect(self._on_snapshot)
        self._worker.error.connect(self._on_error)
        self._thread.start()

        self._connected = True
        self._log("connected to " + ("simulator" if self._sim else target))
        self._update_controls()

    def _disconnect(self) -> None:
        if self._worker is not None and self._thread is not None and self._thread.isRunning():
            QMetaObject.invokeMethod(
                self._worker, "stop", Qt.ConnectionType.BlockingQueuedConnection
            )
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
        self._cleanup_connection()
        self._connected = False
        self._set_banner("DISCONNECTED", "#777")
        self._log("disconnected")
        self._update_controls()

    def _cleanup_connection(self) -> None:
        if self._sim is not None:
            self._sim.stop()
            self._sim = None
        if self._transport is not None:
            try:
                self._transport.close()
            except Exception:
                pass
            self._transport = None
        self._worker = None
        self._thread = None
        self._client = None

    def _read_snapshot_locked(self) -> IoSnapshot:
        # Runs on the worker thread; the lock keeps it from interleaving with
        # operator-initiated output writes on the GUI thread.
        with self._io_lock:
            assert self._client is not None
            return self._client.read_snapshot()

    # --- telemetry handling ---------------------------------------------- #
    @Slot(object)
    def _on_snapshot(self, snap: IoSnapshot) -> None:
        for ch, led in self._di_leds.items():
            led.setStyleSheet(_ON_STYLE if snap.di[ch] else _OFF_STYLE)
        for ch, widget in self._do_widgets.items():
            on = snap.do[ch]
            if isinstance(widget, QPushButton):
                widget.setChecked(on)
                widget.setStyleSheet(_ON_STYLE if on else "")
            else:
                widget.setStyleSheet(self._lamp_style(ch, on))
        for ch, label in self._ai_labels.items():
            label.setText(f"{snap.ai[ch]:.1f}")

        if snap.interlock_ok:
            self._set_banner("INTERLOCK OK", "#27ae60")
        else:
            self._set_banner("INTERLOCK OPEN — motion disabled", "#c0392b")

    @Slot(str)
    def _on_error(self, message: str) -> None:
        self._set_banner(f"COMM ERROR — {message}", "#e67e22")
        self._log(f"[COMM] {message}")

    def _lamp_style(self, ch: int, on: bool) -> str:
        if not on:
            return _OFF_STYLE
        if ch == io_map.DO_LAMP_RED:
            return _RED_STYLE
        if ch == io_map.DO_LAMP_AMBER:
            return _AMBER_STYLE
        return _ON_STYLE

    # --- output / fault control ------------------------------------------ #
    def _on_output_clicked(self, channel: int, checked: bool) -> None:
        if self._client is None:
            return
        try:
            with self._io_lock:
                self._client.set_output(channel, checked)
            self._log(f"set {io_map.DO_NAMES[channel]} = {'ON' if checked else 'OFF'}")
        except ModbusError as exc:
            self._log(f"output {io_map.DO_NAMES[channel]} rejected: {type(exc).__name__}")
            self._do_widgets[channel].setChecked(False)

    def _clear_faults(self) -> None:
        if self._sim is not None:
            self._sim.clear_faults()
            self._log("faults cleared (E-stop reset, area clear)")

    # --- helpers ---------------------------------------------------------- #
    def _set_banner(self, text: str, color: str) -> None:
        self.interlock_banner.setText(text)
        self.interlock_banner.setStyleSheet(
            f"background:{color}; color:white; font-weight:bold; border-radius:4px;"
        )

    def _log(self, message: str) -> None:
        self.log_view.appendPlainText(f"{time.strftime('%H:%M:%S')}  {message}")

    def _update_controls(self) -> None:
        self.connect_btn.setText("Disconnect" if self._connected else "Connect")
        for w in (self.port_combo, self.unit_spin):
            w.setEnabled(not self._connected)
        is_sim = self._connected and self._sim is not None
        for btn in self._fault_buttons:
            btn.setEnabled(is_sim)
        for widget in self._do_widgets.values():
            if isinstance(widget, QPushButton):
                widget.setEnabled(self._connected)

    def shutdown(self) -> None:
        if self._connected:
            self._disconnect()
