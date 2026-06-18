"""A CAN BMS simulator that broadcasts periodic telemetry frames.

Sends frames on any python-can ``Bus`` (use the ``virtual`` interface to run
without hardware). ``import can`` happens here, not in the toolkit's top-level
packages, so python-can stays an optional dependency.
"""

from __future__ import annotations

import threading
import time

import can

from fae_toolkit.protocols.bms.model import BatteryFlag
from fae_toolkit.protocols.canbus import frames

_CELL_MIN_V = 3.20
_CELL_MAX_V = 4.10
_OVER_TEMP_C = 55.0
_OVER_CURRENT_A = 150.0


class CanBmsSimulator:
    """Broadcasts BMS telemetry frames on a CAN bus until stopped."""

    def __init__(
        self,
        bus: can.BusABC,
        *,
        cells: int = 14,
        capacity_ah: float = 50.0,
        initial_soc: float = 85.0,
        load_current: float = -20.0,
        ambient_c: float = 25.0,
        period: float = 0.1,
    ) -> None:
        self.bus = bus
        self.cells = cells
        self.capacity_ah = capacity_ah
        self.period = period

        self._soc = initial_soc
        self._current = load_current
        self._temp = ambient_c
        self._ambient = ambient_c
        self._forced_warnings = BatteryFlag(0)

        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last = time.monotonic()

    # --- lifecycle -------------------------------------------------------- #
    def start(self) -> CanBmsSimulator:
        self._stop.clear()
        self._last = time.monotonic()
        self._thread = threading.Thread(target=self._run, name="can-bms-sim", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def __enter__(self) -> CanBmsSimulator:
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()

    # --- controls --------------------------------------------------------- #
    def set_load_current(self, amps: float) -> None:
        with self._lock:
            self._current = amps

    def force_warning(self, flag: BatteryFlag) -> None:
        with self._lock:
            self._forced_warnings |= flag

    def clear_faults(self) -> None:
        with self._lock:
            self._forced_warnings = BatteryFlag(0)

    # --- main loop -------------------------------------------------------- #
    def _run(self) -> None:
        while not self._stop.is_set():
            now = time.monotonic()
            self._advance(now - self._last)
            self._last = now
            self._broadcast()
            self._stop.wait(self.period)

    def _advance(self, dt: float) -> None:
        if dt <= 0:
            return
        with self._lock:
            self._soc += (self._current * (dt / 3600.0) / self.capacity_ah) * 100.0
            self._soc = max(0.0, min(100.0, self._soc))
            target = self._ambient + abs(self._current) * 0.12
            self._temp += (target - self._temp) * min(1.0, dt * 0.05)

    def _broadcast(self) -> None:
        with self._lock:
            soc = self._soc
            current = self._current
            temp = self._temp
            cell_v = _CELL_MIN_V + (_CELL_MAX_V - _CELL_MIN_V) * (soc / 100.0)
            voltage = cell_v * self.cells
            warnings = self._forced_warnings
            if temp > _OVER_TEMP_C:
                warnings |= BatteryFlag.OVER_TEMP
            if current < -_OVER_CURRENT_A:
                warnings |= BatteryFlag.OVER_CURRENT_DISCHARGE

        self.bus.send(
            can.Message(
                arbitration_id=frames.CAN_ID_TELEM_A,
                data=frames.encode_telem_a(voltage, current, soc),
                is_extended_id=False,
            )
        )
        self.bus.send(
            can.Message(
                arbitration_id=frames.CAN_ID_TELEM_B,
                data=frames.encode_telem_b(temp, temp - 2.0, warnings),
                is_extended_id=False,
            )
        )
