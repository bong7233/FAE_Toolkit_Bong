"""A remote-IO / PIO interlock simulator answering Modbus-RTU requests.

Serves digital inputs (sensors / PIO request lines, function 0x02), coils
(actuators + light tower, 0x01/0x05) and analog inputs (0x04). It enforces a
safety interlock — motion outputs are rejected while the E-stop is tripped or
the safety area is blocked — and drives a light tower from the machine state,
mirroring the interlock checks done during teaching and commissioning.
"""

from __future__ import annotations

import math
import random

from fae_toolkit.core.transport import Transport
from fae_toolkit.protocols import modbus
from fae_toolkit.protocols.io import map as io_map
from fae_toolkit.sim.base import ModbusDeviceSimulator


class IoSimulator(ModbusDeviceSimulator):
    """Simulated remote-IO block bound to a :class:`Transport`."""

    def __init__(
        self,
        transport: Transport,
        unit_id: int = 1,
        *,
        poll_interval: float = 0.01,
        seed: int | None = 7,
    ) -> None:
        super().__init__(transport, unit_id, poll_interval=poll_interval)
        self._rng = random.Random(seed)
        self._di = [False] * io_map.DI_COUNT
        self._do = [False] * io_map.DO_COUNT
        self._ai = [0] * io_map.AI_COUNT
        self._elapsed = 0.0

        # Safe, idle defaults.
        for ch in (
            io_map.DI_ES,
            io_map.DI_AREA_CLEAR,
            io_map.DI_READY,
            io_map.DI_HO_AVBL,
            io_map.DI_CS0,
            io_map.DI_L_REQ,
        ):
            self._di[ch] = True
        self._recompute()

    @property
    def _interlock_ok(self) -> bool:
        return self._di[io_map.DI_ES] and self._di[io_map.DI_AREA_CLEAR]

    # --- control / fault injection (thread-safe) -------------------------- #
    def trip_estop(self, tripped: bool = True) -> None:
        with self._lock:
            self._di[io_map.DI_ES] = not tripped
            self._recompute()

    def set_area_blocked(self, blocked: bool = True) -> None:
        with self._lock:
            self._di[io_map.DI_AREA_CLEAR] = not blocked
            self._recompute()

    def set_input(self, channel: int, value: bool) -> None:
        with self._lock:
            if 0 <= channel < io_map.DI_COUNT:
                self._di[channel] = bool(value)
                self._recompute()

    def clear_faults(self) -> None:
        super().clear_faults()
        with self._lock:
            self._di[io_map.DI_ES] = True
            self._di[io_map.DI_AREA_CLEAR] = True
            self._recompute()

    # --- Modbus handling -------------------------------------------------- #
    def _respond(self, frame: bytes) -> bytes | None:
        return modbus.process_request(
            frame,
            self.unit_id,
            read_discrete=self._read_di,
            read_coils=self._read_do,
            read_input=self._read_ai,
            write_coil=self._write_do,
        )

    def _read_di(self, start: int, count: int) -> list[bool]:
        if start < 0 or start + count > io_map.DI_COUNT:
            raise modbus.IllegalDataAddress()
        with self._lock:
            return self._di[start : start + count]

    def _read_do(self, start: int, count: int) -> list[bool]:
        if start < 0 or start + count > io_map.DO_COUNT:
            raise modbus.IllegalDataAddress()
        with self._lock:
            return self._do[start : start + count]

    def _read_ai(self, start: int, count: int) -> list[int]:
        if start < 0 or start + count > io_map.AI_COUNT:
            raise modbus.IllegalDataAddress()
        with self._lock:
            return self._ai[start : start + count]

    def _write_do(self, channel: int, on: bool) -> None:
        if not 0 <= channel < io_map.DO_COUNT:
            raise modbus.IllegalDataAddress()
        with self._lock:
            if on and channel in io_map.MOTION_OUTPUTS and not self._interlock_ok:
                # Interlock open: refuse to actuate a motion output.
                raise modbus.IllegalDataValue()
            self._do[channel] = on
            self._recompute()

    # --- physics ---------------------------------------------------------- #
    def _tick(self, dt: float) -> None:
        if dt <= 0:
            return
        with self._lock:
            self._elapsed += dt
            distance = 250.0 + 50.0 * math.sin(self._elapsed * 0.7) + self._rng.uniform(-0.5, 0.5)
            pressure = 101.3 + self._rng.uniform(-0.3, 0.3)
            lifted = self._do[io_map.DO_LIFT_UP] and self._do[io_map.DO_LOAD_CLAMP]
            weight = 12.5 if lifted else 0.0
            temp = (
                25.0 + (3.0 if self._do[io_map.DO_CONVEYOR] else 0.0) + self._rng.uniform(-0.2, 0.2)
            )
            self._ai[io_map.AI_DISTANCE] = int(round(distance / io_map.AI_SCALE))
            self._ai[io_map.AI_PRESSURE] = int(round(pressure / io_map.AI_SCALE))
            self._ai[io_map.AI_WEIGHT] = int(round(weight / io_map.AI_SCALE))
            self._ai[io_map.AI_TEMP] = int(round(temp / io_map.AI_SCALE))
            self._recompute()

    def _recompute(self) -> None:
        """Drive the light tower from the current machine state."""
        moving = any(self._do[ch] for ch in io_map.MOTION_OUTPUTS)
        self._do[io_map.DO_LAMP_RED] = not self._interlock_ok
        self._do[io_map.DO_LAMP_AMBER] = self._interlock_ok and moving
        self._do[io_map.DO_LAMP_GREEN] = self._interlock_ok and not moving
