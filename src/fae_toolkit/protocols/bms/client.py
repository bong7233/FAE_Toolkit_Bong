"""High-level BMS client built on the Modbus-RTU transport."""

from __future__ import annotations

from fae_toolkit.core.transport import Transport
from fae_toolkit.protocols import modbus
from fae_toolkit.protocols.bms import registers as reg
from fae_toolkit.protocols.bms.model import BatteryTelemetry, decode_summary


class BmsClient:
    """Reads battery telemetry from a BMS over any :class:`Transport`.

    The same client works against a real serial port or the in-process
    :class:`~fae_toolkit.sim.bms.BmsSimulator`.
    """

    def __init__(self, transport: Transport, unit_id: int = 1, timeout: float = 1.0) -> None:
        self.transport = transport
        self.unit_id = unit_id
        self.timeout = timeout

    def read_telemetry(self) -> BatteryTelemetry:
        """Read and decode the pack-level summary block."""
        values = modbus.read_holding_registers(
            self.transport,
            self.unit_id,
            reg.SUMMARY_START,
            reg.SUMMARY_COUNT,
            timeout=self.timeout,
        )
        return decode_summary(values)

    def read_cell_voltages(self, count: int = reg.MAX_CELLS) -> list[int]:
        """Read per-cell voltages in millivolts."""
        count = max(1, min(count, reg.MAX_CELLS))
        return modbus.read_holding_registers(
            self.transport,
            self.unit_id,
            reg.CELL_VOLTAGES_START,
            count,
            timeout=self.timeout,
        )
