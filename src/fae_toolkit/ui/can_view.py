"""CAN BMS test panel.

Connects to the built-in CAN simulator over python-can's in-process ``virtual``
bus (no hardware) or a real interface (e.g. socketcan, pcan), shows live
telemetry and trends, and can inject faults against the simulator.
"""

from __future__ import annotations

import time
from collections import deque

import can
import pyqtgraph as pg
from PySide6.QtCore import QMetaObject, Qt, QThread, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from fae_toolkit.protocols.bms.model import BatteryFlag
from fae_toolkit.protocols.canbus import CanBmsClient
from fae_toolkit.protocols.canbus.model import CanBmsState
from fae_toolkit.sim.can_bms import CanBmsSimulator
from fae_toolkit.ui.worker import PollWorker

_MAXLEN = 600


class CanView(QWidget):
    """Self-contained CAN BMS test view."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sim: CanBmsSimulator | None = None
        self._app_bus: can.BusABC | None = None
        self._dev_bus: can.BusABC | None = None
        self._client: CanBmsClient | None = None
        self._thread: QThread | None = None
        self._worker: PollWorker | None = None
        self._connected = False
        self._t0 = 0.0
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
        self.iface_combo = QComboBox()
        self.iface_combo.addItems(["virtual", "socketcan", "pcan", "kvaser"])
        self.iface_combo.setEditable(True)
        self.channel_edit = QLineEdit("fae_gui")
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(50, 5000)
        self.interval_spin.setSingleStep(50)
        self.interval_spin.setValue(300)
        self.interval_spin.setSuffix(" ms")
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._toggle_connection)
        form.addRow("Interface", self.iface_combo)
        form.addRow("Channel", self.channel_edit)
        form.addRow("Poll", self.interval_spin)
        form.addRow(self.connect_btn)
        return box

    def _build_readout_group(self) -> QGroupBox:
        box = QGroupBox("실시간 측정값 (Live telemetry)")
        grid = QGridLayout(box)
        fields = [
            ("voltage", "Pack V"),
            ("current", "Pack A"),
            ("power", "Power W"),
            ("soc", "SOC %"),
            ("max_temp", "T max ℃"),
        ]
        for idx, (key, label) in enumerate(fields):
            grid.addWidget(QLabel(label), idx, 0)
            value = QLabel("—")
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(value, idx, 1)
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
            ("Heavy discharge", lambda: self._sim and self._sim.set_load_current(-160.0)),
            (
                "Force OVER_TEMP",
                lambda: self._sim and self._sim.force_warning(BatteryFlag.OVER_TEMP),
            ),
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
        layout.addWidget(self.log_view)
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
        interface = self.iface_combo.currentText().strip() or "virtual"
        channel = self.channel_edit.text().strip() or "fae_gui"
        try:
            if interface == "virtual":
                self._dev_bus = can.Bus(
                    interface="virtual", channel=channel, receive_own_messages=False
                )
                self._app_bus = can.Bus(
                    interface="virtual", channel=channel, receive_own_messages=False
                )
                self._sim = CanBmsSimulator(self._dev_bus)
                self._sim.start()
            else:
                self._dev_bus = None
                self._sim = None
                self._app_bus = can.Bus(interface=interface, channel=channel)
        except Exception as exc:
            self._log(f"connect failed: {exc}")
            self._cleanup_connection()
            return

        self._client = CanBmsClient(self._app_bus, timeout=1.0)
        self._thread = QThread(self)
        self._worker = PollWorker(self._client.read_state, interval_ms=self.interval_spin.value())
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.start)
        self._thread.finished.connect(self._worker.deleteLater)
        self._worker.result.connect(self._on_state)
        self._worker.error.connect(self._on_error)
        self._thread.start()

        self._connected = True
        self._t0 = time.monotonic()
        self._t.clear()
        self._v.clear()
        self._i.clear()
        self._log(f"connected to {interface}:{channel}")
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
        for bus_attr in ("_app_bus", "_dev_bus"):
            bus = getattr(self, bus_attr)
            if bus is not None:
                try:
                    bus.shutdown()
                except Exception:
                    pass
                setattr(self, bus_attr, None)
        self._worker = None
        self._thread = None
        self._client = None

    # --- telemetry handling ---------------------------------------------- #
    @Slot(object)
    def _on_state(self, state: CanBmsState) -> None:
        v = self._values
        v["voltage"].setText(f"{state.voltage:6.2f}")
        v["current"].setText(f"{state.current:+7.2f}")
        v["power"].setText(f"{state.power:+7.0f}")
        v["soc"].setText(f"{state.soc:5.1f}")
        v["max_temp"].setText(f"{state.max_temp:5.1f}")

        if state.has_alarm:
            self._set_banner("ALARM: " + ", ".join(state.active_flags()), "#c0392b")
        else:
            self._set_banner("NORMAL", "#27ae60")

        t = time.monotonic() - self._t0
        self._t.append(t)
        self._v.append(state.voltage)
        self._i.append(state.current)
        self.curve_v.setData(list(self._t), list(self._v))
        self.curve_i.setData(list(self._t), list(self._i))

    @Slot(str)
    def _on_error(self, message: str) -> None:
        self._set_banner(f"CAN ERROR — {message}", "#e67e22")
        self._log(f"[CAN] {message}")

    def _clear_faults(self) -> None:
        if self._sim is not None:
            self._sim.clear_faults()
            self._sim.set_load_current(-20.0)
            self._log("faults cleared, load reset to -20 A")

    # --- helpers ---------------------------------------------------------- #
    def _set_banner(self, text: str, color: str) -> None:
        self.alarm_banner.setText(text)
        self.alarm_banner.setStyleSheet(
            f"background:{color}; color:white; font-weight:bold; border-radius:4px;"
        )

    def _log(self, message: str) -> None:
        self.log_view.appendPlainText(f"{time.strftime('%H:%M:%S')}  {message}")

    def _update_controls(self) -> None:
        self.connect_btn.setText("Disconnect" if self._connected else "Connect")
        for w in (self.iface_combo, self.channel_edit):
            w.setEnabled(not self._connected)
        is_sim = self._connected and self._sim is not None
        for btn in self._fault_buttons:
            btn.setEnabled(is_sim)

    def shutdown(self) -> None:
        if self._connected:
            self._disconnect()
