"""A BMS device simulator that answers Modbus-RTU requests over a transport.

The simulator models a series battery pack that discharges over time: cell
voltage sags with state-of-charge, temperature rises under load, and cells are
slightly imbalanced. It serves the same register map a real BMS exposes, so the
application talks to it through the identical code path.

Fault injection (comm timeouts, CRC corruption, forced alarm flags) lets the
toolkit demonstrate field troubleshooting scenarios on demand.
"""

from __future__ import annotations

import random
import threading
import time

from fae_toolkit.core.crc import check_crc
from fae_toolkit.core.transport import Transport
from fae_toolkit.protocols import modbus
from fae_toolkit.protocols.bms import registers as reg
from fae_toolkit.protocols.bms.model import BatteryFlag

# Cell chemistry / threshold constants (Li-ion-ish, tuned for clear demos).
_CELL_MIN_V = 3.20
_CELL_MAX_V = 4.10
_OVER_VOLTAGE_MV = 4150
_UNDER_VOLTAGE_MV = 3050
_OVER_TEMP_C = 55.0
_UNDER_TEMP_C = 0.0
_IMBALANCE_MV = 50
_OVER_CURRENT_A = 150.0


class BmsSimulator:
    """Simulated BMS bound to a :class:`Transport`.

    Use as a context manager, or call :meth:`start` / :meth:`stop` explicitly::

        app_end, dev_end = create_loopback_pair()
        with BmsSimulator(dev_end):
            client = BmsClient(app_end)
            print(client.read_telemetry())
    """

    def __init__(
        self,
        transport: Transport,
        unit_id: int = 1,
        *,
        cells: int = 14,
        capacity_ah: float = 50.0,
        initial_soc: float = 85.0,
        load_current: float = -20.0,
        ambient_c: float = 25.0,
        cycle_count: int = 312,
        soh: float = 98.0,
        poll_interval: float = 0.01,
        seed: int | None = 42,
    ) -> None:
        self.transport = transport
        self.unit_id = unit_id
        self.cells = cells
        self.capacity_ah = capacity_ah
        self.poll_interval = poll_interval

        rng = random.Random(seed)
        # Fixed per-cell offsets (mV) create a realistic, stable imbalance.
        self._cell_offsets = [rng.uniform(-12, 12) for _ in range(cells)]

        # Mutable physical state.
        self._soc = initial_soc
        self._soh = soh
        self._current = load_current
        self._temp = ambient_c
        self._ambient = ambient_c
        self._cycle = cycle_count

        # Fault-injection state.
        self._drop_responses = 0
        self._corrupt_next = False
        self._forced_warnings = BatteryFlag(0)
        self._forced_protections = BatteryFlag(0)

        self._registers = [0] * reg.REGISTER_SPAN
        self._buffer = bytearray()
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_tick = time.monotonic()
        self._recompute()

    # --- lifecycle -------------------------------------------------------- #
    def start(self) -> BmsSimulator:
        if not self.transport.is_open:
            self.transport.open()
        self._stop.clear()
        self._last_tick = time.monotonic()
        self._thread = threading.Thread(target=self._run, name="bms-sim", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def __enter__(self) -> BmsSimulator:
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()

    # --- fault injection (thread-safe) ------------------------------------ #
    def inject_comm_timeout(self, count: int = 1) -> None:
        """Drop the next *count* responses, simulating a comm timeout."""
        with self._lock:
            self._drop_responses += count

    def inject_crc_error(self) -> None:
        """Corrupt the CRC of the next response."""
        with self._lock:
            self._corrupt_next = True

    def force_warning(self, flag: BatteryFlag) -> None:
        with self._lock:
            self._forced_warnings |= flag
            self._recompute()

    def force_protection(self, flag: BatteryFlag) -> None:
        with self._lock:
            self._forced_protections |= flag
            self._recompute()

    def clear_faults(self) -> None:
        with self._lock:
            self._drop_responses = 0
            self._corrupt_next = False
            self._forced_warnings = BatteryFlag(0)
            self._forced_protections = BatteryFlag(0)
            self._recompute()

    def set_load_current(self, amps: float) -> None:
        """Set pack current (negative = discharge, positive = charge)."""
        with self._lock:
            self._current = amps

    # --- main loop -------------------------------------------------------- #
    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                data = self.transport.read(64, timeout=self.poll_interval)
            except RuntimeError:
                break  # transport closed
            now = time.monotonic()
            self._advance(now - self._last_tick)
            self._last_tick = now
            if data:
                self._buffer.extend(data)
                self._process_buffer()

    def _process_buffer(self) -> None:
        while len(self._buffer) >= modbus.request_length(modbus.READ_HOLDING_REGISTERS):
            frame = bytes(self._buffer[:8])
            if check_crc(frame):
                del self._buffer[:8]
                response = modbus.process_request(
                    frame,
                    self.unit_id,
                    read_holding=self._read_holding,
                    write_holding=self._write_holding,
                )
                if response is not None:
                    self._send(response)
            else:
                del self._buffer[0]  # resync on noise

    def _send(self, response: bytes) -> None:
        with self._lock:
            if self._drop_responses > 0:
                self._drop_responses -= 1
                return
            if self._corrupt_next:
                self._corrupt_next = False
                response = response[:-1] + bytes([response[-1] ^ 0xFF])
        self.transport.write(response)

    # --- register access (called by modbus.process_request) --------------- #
    def _read_holding(self, start: int, count: int) -> list[int]:
        end = start + count
        if start < 0 or end > reg.REGISTER_SPAN:
            raise modbus.IllegalDataAddress()
        with self._lock:
            return self._registers[start:end]

    def _write_holding(self, address: int, value: int) -> None:
        if not 0 <= address < reg.REGISTER_SPAN:
            raise modbus.IllegalDataAddress()
        with self._lock:
            self._registers[address] = value & 0xFFFF

    # --- physics ---------------------------------------------------------- #
    def _advance(self, dt: float) -> None:
        if dt <= 0:
            return
        with self._lock:
            # Coulomb counting: SOC change from current over elapsed time.
            self._soc += (self._current * (dt / 3600.0) / self.capacity_ah) * 100.0
            self._soc = max(0.0, min(100.0, self._soc))
            # First-order thermal model: heating with load, relaxing to ambient.
            target = self._ambient + abs(self._current) * 0.12
            self._temp += (target - self._temp) * min(1.0, dt * 0.05)
            self._recompute()

    def _recompute(self) -> None:
        """Recompute the register image from the current physical state."""
        soc_frac = self._soc / 100.0
        base_mv = (_CELL_MIN_V + (_CELL_MAX_V - _CELL_MIN_V) * soc_frac) * 1000.0
        cell_mv = [int(round(base_mv + off)) for off in self._cell_offsets]
        max_mv, min_mv = max(cell_mv), min(cell_mv)
        pack_voltage = sum(cell_mv) / 1000.0  # V

        warnings = self._forced_warnings
        if max_mv > _OVER_VOLTAGE_MV:
            warnings |= BatteryFlag.OVER_VOLTAGE
        if min_mv < _UNDER_VOLTAGE_MV:
            warnings |= BatteryFlag.UNDER_VOLTAGE
        if self._temp > _OVER_TEMP_C:
            warnings |= BatteryFlag.OVER_TEMP
        if self._temp < _UNDER_TEMP_C:
            warnings |= BatteryFlag.UNDER_TEMP
        if (max_mv - min_mv) > _IMBALANCE_MV:
            warnings |= BatteryFlag.CELL_IMBALANCE
        if self._current < -_OVER_CURRENT_A:
            warnings |= BatteryFlag.OVER_CURRENT_DISCHARGE
        if self._current > _OVER_CURRENT_A:
            warnings |= BatteryFlag.OVER_CURRENT_CHARGE

        r = self._registers
        r[reg.REG_PACK_VOLTAGE] = int(round(pack_voltage / reg.SCALE_VOLTAGE))
        r[reg.REG_PACK_CURRENT] = reg.to_unsigned16(int(round(self._current / reg.SCALE_CURRENT)))
        r[reg.REG_SOC] = int(round(self._soc / reg.SCALE_PERCENT))
        r[reg.REG_SOH] = int(round(self._soh / reg.SCALE_PERCENT))
        capacity = self._soc / 100.0 * self.capacity_ah
        r[reg.REG_REMAINING_CAPACITY] = int(round(capacity / reg.SCALE_CAPACITY))
        r[reg.REG_CYCLE_COUNT] = self._cycle
        r[reg.REG_MAX_CELL_MV] = max_mv
        r[reg.REG_MIN_CELL_MV] = min_mv
        r[reg.REG_MAX_TEMP] = reg.to_unsigned16(int(round(self._temp / reg.SCALE_TEMP)))
        r[reg.REG_MIN_TEMP] = reg.to_unsigned16(int(round((self._temp - 2.0) / reg.SCALE_TEMP)))
        r[reg.REG_WARNING_FLAGS] = int(warnings)
        r[reg.REG_PROTECTION_FLAGS] = int(self._forced_protections)
        for i, mv in enumerate(cell_mv):
            r[reg.CELL_VOLTAGES_START + i] = mv
        for i in range(reg.MAX_TEMPS):
            r[reg.TEMPS_START + i] = reg.to_unsigned16(
                int(round((self._temp - i) / reg.SCALE_TEMP))
            )
