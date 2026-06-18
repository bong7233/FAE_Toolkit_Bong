"""Decoded CAN BMS telemetry."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from fae_toolkit.protocols.bms.model import BatteryFlag


@dataclass(slots=True)
class CanBmsState:
    """Merged view of the periodic CAN telemetry frames."""

    voltage: float
    current: float
    soc: float
    max_temp: float = 0.0
    min_temp: float = 0.0
    warnings: BatteryFlag = BatteryFlag(0)
    timestamp: float = field(default_factory=time.time)

    @property
    def power(self) -> float:
        return self.voltage * self.current

    @property
    def has_alarm(self) -> bool:
        return bool(self.warnings)

    def active_flags(self) -> list[str]:
        return self.warnings.labels()
