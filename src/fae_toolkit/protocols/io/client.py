"""High-level remote-IO client built on Modbus RTU."""

from __future__ import annotations

from fae_toolkit.core.transport import Transport
from fae_toolkit.protocols import modbus
from fae_toolkit.protocols.io import map as io_map
from fae_toolkit.protocols.io.model import IoSnapshot


class IoClient:
    """Reads/writes a remote-IO block over any :class:`Transport`."""

    def __init__(self, transport: Transport, unit_id: int = 1, timeout: float = 1.0) -> None:
        self.transport = transport
        self.unit_id = unit_id
        self.timeout = timeout

    def read_inputs(self, count: int = io_map.DI_COUNT) -> list[bool]:
        return modbus.read_discrete_inputs(self.transport, self.unit_id, 0, count, self.timeout)

    def read_outputs(self, count: int = io_map.DO_COUNT) -> list[bool]:
        return modbus.read_coils(self.transport, self.unit_id, 0, count, self.timeout)

    def read_analog(self, count: int = io_map.AI_COUNT) -> list[float]:
        raw = modbus.read_input_registers(self.transport, self.unit_id, 0, count, self.timeout)
        return [v * io_map.AI_SCALE for v in raw]

    def set_output(self, channel: int, on: bool) -> None:
        """Set a digital output. Raises :class:`modbus.ModbusException` if the
        device rejects it (e.g. an interlock violation)."""
        modbus.write_single_coil(self.transport, self.unit_id, channel, on, self.timeout)

    def read_snapshot(self) -> IoSnapshot:
        return IoSnapshot(
            di=self.read_inputs(),
            do=self.read_outputs(),
            ai=self.read_analog(),
        )
