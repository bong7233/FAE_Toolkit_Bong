"""Battery (BMS) communication test panel.

Connect to the built-in simulator (no hardware) or a real serial port, watch
live telemetry and trends, exercise fault scenarios, and record to CSV.
"""

from __future__ import annotations

import time
from collections import deque

import pyqtgraph as pg
from PySide6.QtCore import QMetaObject, Qt, QThread, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
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
from fae_toolkit.protocols.bms import BmsClient
from fae_toolkit.protocols.bms.model import BatteryFlag, BatteryTelemetry
from fae_toolkit.services.csv_logger import CsvLogger
from fae_toolkit.sim.bms import BmsSimulator
from fae_toolkit.ui.worker import BmsPollWorker

SIM_LABEL = "Simulator (no hardware)"
_MAXLEN = 600


def _list_serial_ports() -> list[str]:
    try:
        from serial.tools import list_ports

        return [p.device for p in list_ports.comports()]
    except Exception:
        return []


class BatteryView(QWidget):
    """Self-contained BMS test view."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sim: BmsSimulator | None = None
        self._transport = None
        self._thread: QThread | None = None
        self._worker: BmsPollWorker | None = None
        self._connected = False
        self._t0 = 0.0
        self._csv: CsvLogger | None = None

        self._t: deque[float] = deque(maxlen=_MAXLEN)
        self._v: deque[float] = deque(maxlen=_MAXLEN)
        self._i: deque[float] = deque(maxlen=_MAXLEN)

        self._values: dict[str, QLabel] = {}
        self._build_ui()
        self._update_controls()

    # --- UI construction -------------------------------------------------- #
    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        left = QVBoxLayout()
        left.addWidget(self._build_connection_group())
        left.addWidget(self._build_readout_group())
        left.addWidget(self._build_alarm_banner())
        left.addWidget(self._build_fault_group())
        left.addWidget(self._build_log_group(), stretch=1)
        root.addLayout(left, stretch=0)
        root.addWidget(self._build_plots(), stretch=1)

    def _build_connection_group(self) -> QGroupBox:
        box = QGroupBox("연결 (Connection)")
        form = QFormLayout(box)
        self.port_combo = QComboBox()
        self.port_combo.addItem(SIM_LABEL)
        self.port_combo.addItems(_list_serial_ports())
        self.port_combo.setEditable(True)

        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])

        self.unit_spin = QSpinBox()
        self.unit_spin.setRange(1, 247)
        self.unit_spin.setValue(1)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(50, 5000)
        self.interval_spin.setSingleStep(50)
        self.interval_spin.setValue(500)
        self.interval_spin.setSuffix(" ms")

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._toggle_connection)

        form.addRow("Port", self.port_combo)
        form.addRow("Baud", self.baud_combo)
        form.addRow("Unit id", self.unit_spin)
        form.addRow("Poll", self.interval_spin)
        form.addRow(self.connect_btn)
        return box

    def _build_readout_group(self) -> QGroupBox:
        box = QGroupBox("실시간 측정값 (Live telemetry)")
        grid = QGridLayout(box)
        mono = QFont("monospace")
        mono.setStyleHint(QFont.StyleHint.TypeWriter)
        fields = [
            ("pack_voltage", "Pack V"),
            ("pack_current", "Pack A"),
            ("power", "Power W"),
            ("soc", "SOC %"),
            ("soh", "SOH %"),
            ("remaining", "Rem Ah"),
            ("max_temp", "T max ℃"),
            ("min_temp", "T min ℃"),
            ("cell_delta", "ΔCell mV"),
            ("cycles", "Cycles"),
        ]
        for idx, (key, label) in enumerate(fields):
            row, col = divmod(idx, 2)
            grid.addWidget(QLabel(label), row, col * 2)
            value = QLabel("—")
            value.setFont(mono)
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(value, row, col * 2 + 1)
            self._values[key] = value
        return box

    def _build_alarm_banner(self) -> QLabel:
        self.alarm_banner = QLabel("DISCONNECTED")
        self.alarm_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.alarm_banner.setMinimumHeight(34)
        self._set_banner("DISCONNECTED", "#777")
        return self.alarm_banner

    def _build_fault_group(self) -> QGroupBox:
        box = QGroupBox("고장 주입 (Fault injection · simulator only)")
        layout = QGridLayout(box)
        self._fault_buttons: list[QPushButton] = []
        specs = [
            ("Comm timeout", lambda: self._sim and self._sim.inject_comm_timeout(1)),
            ("CRC error", lambda: self._sim and self._sim.inject_crc_error()),
            (
                "Force OVER_TEMP",
                lambda: self._sim and self._sim.force_warning(BatteryFlag.OVER_TEMP),
            ),
            ("Heavy discharge", lambda: self._sim and self._sim.set_load_current(-160.0)),
            ("Clear faults", self._clear_faults),
        ]
        for idx, (label, fn) in enumerate(specs):
            btn = QPushButton(label)
            btn.clicked.connect(fn)
            layout.addWidget(btn, idx // 2, idx % 2)
            self._fault_buttons.append(btn)
        return box

    def _build_log_group(self) -> QGroupBox:
        box = QGroupBox("이벤트 로그 (Event log)")
        layout = QVBoxLayout(box)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(500)
        self.csv_btn = QPushButton("Start CSV recording")
        self.csv_btn.clicked.connect(self._toggle_csv)
        layout.addWidget(self.log_view)
        layout.addWidget(self.csv_btn)
        return box

    def _build_plots(self) -> QWidget:
        pg.setConfigOptions(antialias=True)
        container = QWidget()
        layout = QVBoxLayout(container)
        self.plot_v = pg.PlotWidget(title="Pack voltage (V)")
        self.plot_v.showGrid(x=True, y=True, alpha=0.3)
        self.plot_v.setLabel("bottom", "time", "s")
        self.curve_v = self.plot_v.plot(pen=pg.mkPen("#2e86de", width=2))

        self.plot_i = pg.PlotWidget(title="Pack current (A)")
        self.plot_i.showGrid(x=True, y=True, alpha=0.3)
        self.plot_i.setLabel("bottom", "time", "s")
        self.plot_i.setXLink(self.plot_v)
        self.curve_i = self.plot_i.plot(pen=pg.mkPen("#e74c3c", width=2))

        layout.addWidget(self.plot_v)
        layout.addWidget(self.plot_i)
        return container

    # --- connection lifecycle -------------------------------------------- #
    def _toggle_connection(self) -> None:
        self._disconnect() if self._connected else self._connect()

    def _connect(self) -> None:
        target = self.port_combo.currentText().strip()
        try:
            if target == SIM_LABEL:
                app_end, dev_end = create_loopback_pair()
                self._sim = BmsSimulator(dev_end, unit_id=self.unit_spin.value())
                self._sim.start()
                self._transport = app_end
            else:
                self._sim = None
                self._transport = SerialTransport(
                    target, baudrate=int(self.baud_combo.currentText())
                )
                self._transport.open()
        except Exception as exc:
            self._log(f"connect failed: {exc}")
            self._cleanup_connection()
            return

        client = BmsClient(self._transport, unit_id=self.unit_spin.value(), timeout=1.0)
        self._thread = QThread(self)
        self._worker = BmsPollWorker(client, interval_ms=self.interval_spin.value())
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.start)
        self._thread.finished.connect(self._worker.deleteLater)
        self._worker.telemetry.connect(self._on_telemetry)
        self._worker.error.connect(self._on_error)
        self._thread.start()

        self._connected = True
        self._t0 = time.monotonic()
        self._t.clear()
        self._v.clear()
        self._i.clear()
        self._log("connected to " + ("simulator" if self._sim else target))
        self._update_controls()

    def _disconnect(self) -> None:
        if self._worker is not None and self._thread is not None and self._thread.isRunning():
            # Stop the timer on the worker's own thread so the QTimer is torn
            # down where it was created (avoids cross-thread timer warnings).
            QMetaObject.invokeMethod(
                self._worker, "stop", Qt.ConnectionType.BlockingQueuedConnection
            )
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
        self._cleanup_connection()
        self._stop_csv()
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

    # --- telemetry handling ---------------------------------------------- #
    @Slot(BatteryTelemetry)
    def _on_telemetry(self, tel: BatteryTelemetry) -> None:
        v = self._values
        v["pack_voltage"].setText(f"{tel.pack_voltage:6.2f}")
        v["pack_current"].setText(f"{tel.pack_current:+7.2f}")
        v["power"].setText(f"{tel.power:+7.0f}")
        v["soc"].setText(f"{tel.soc:5.1f}")
        v["soh"].setText(f"{tel.soh:5.1f}")
        v["remaining"].setText(f"{tel.remaining_capacity:5.2f}")
        v["max_temp"].setText(f"{tel.max_temp:5.1f}")
        v["min_temp"].setText(f"{tel.min_temp:5.1f}")
        v["cell_delta"].setText(f"{tel.cell_delta_mv:4d}")
        v["cycles"].setText(f"{tel.cycle_count:4d}")

        if tel.has_alarm:
            self._set_banner("ALARM: " + ", ".join(tel.active_flags()), "#c0392b")
        else:
            self._set_banner("NORMAL", "#27ae60")

        t = time.monotonic() - self._t0
        self._t.append(t)
        self._v.append(tel.pack_voltage)
        self._i.append(tel.pack_current)
        self.curve_v.setData(list(self._t), list(self._v))
        self.curve_i.setData(list(self._t), list(self._i))

        if self._csv is not None:
            self._csv.write(tel)

    @Slot(str)
    def _on_error(self, message: str) -> None:
        self._set_banner(f"COMM ERROR — {message}", "#e67e22")
        self._log(f"[COMM] {message}")

    # --- fault injection / csv ------------------------------------------- #
    def _clear_faults(self) -> None:
        if self._sim is not None:
            self._sim.clear_faults()
            self._sim.set_load_current(-20.0)
            self._log("faults cleared, load reset to -20 A")

    def _toggle_csv(self) -> None:
        if self._csv is not None:
            self._stop_csv()
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save telemetry CSV", "bms_telemetry.csv", "CSV (*.csv)"
        )
        if not path:
            return
        self._csv = CsvLogger(path)
        self.csv_btn.setText("Stop CSV recording")
        self._log(f"recording CSV -> {path}")

    def _stop_csv(self) -> None:
        if self._csv is not None:
            rows = self._csv.rows
            self._csv.close()
            self._csv = None
            self.csv_btn.setText("Start CSV recording")
            self._log(f"CSV saved ({rows} rows)")

    # --- small helpers ---------------------------------------------------- #
    def _set_banner(self, text: str, color: str) -> None:
        self.alarm_banner.setText(text)
        self.alarm_banner.setStyleSheet(
            f"background:{color}; color:white; font-weight:bold; border-radius:4px;"
        )

    def _log(self, message: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"{stamp}  {message}")

    def _update_controls(self) -> None:
        self.connect_btn.setText("Disconnect" if self._connected else "Connect")
        for w in (self.port_combo, self.baud_combo, self.unit_spin):
            w.setEnabled(not self._connected)
        is_sim = self._connected and self._sim is not None
        for btn in self._fault_buttons:
            btn.setEnabled(is_sim)

    def shutdown(self) -> None:
        """Called by the main window on close to release threads/ports."""
        if self._connected:
            self._disconnect()
