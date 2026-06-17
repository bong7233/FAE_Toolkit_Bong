"""BMS telemetry data model and register decoding."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import IntFlag

from fae_toolkit.protocols.bms import registers as reg


class BatteryFlag(IntFlag):
    """Warning / protection bit flags reported by the BMS."""

    OVER_VOLTAGE = 1 << 0
    UNDER_VOLTAGE = 1 << 1
    OVER_CURRENT_CHARGE = 1 << 2
    OVER_CURRENT_DISCHARGE = 1 << 3
    OVER_TEMP = 1 << 4
    UNDER_TEMP = 1 << 5
    CELL_IMBALANCE = 1 << 6
    COMM_WARNING = 1 << 7

    def labels(self) -> list[str]:
        """Human-readable names of the set flags."""
        return [flag.name for flag in BatteryFlag if flag in self and flag.name]


@dataclass(slots=True)
class BatteryTelemetry:
    """Decoded pack-level battery telemetry in engineering units."""

    timestamp: float
    pack_voltage: float  # V
    pack_current: float  # A (positive = charge, negative = discharge)
    soc: float  # %
    soh: float  # %
    remaining_capacity: float  # Ah
    cycle_count: int
    max_cell_mv: int  # mV
    min_cell_mv: int  # mV
    max_temp: float  # deg C
    min_temp: float  # deg C
    warnings: BatteryFlag = BatteryFlag(0)
    protections: BatteryFlag = BatteryFlag(0)

    @property
    def power(self) -> float:
        """Instantaneous pack power in watts (positive = charging)."""
        return self.pack_voltage * self.pack_current

    @property
    def cell_delta_mv(self) -> int:
        """Spread between the highest and lowest cell, in millivolts."""
        return self.max_cell_mv - self.min_cell_mv

    @property
    def has_alarm(self) -> bool:
        return bool(self.warnings) or bool(self.protections)

    def active_flags(self) -> list[str]:
        """All active warning and protection labels."""
        return self.warnings.labels() + [f"PROT_{n}" for n in self.protections.labels()]


def decode_summary(values: list[int], timestamp: float | None = None) -> BatteryTelemetry:
    """Decode the 12-register summary block into :class:`BatteryTelemetry`."""
    if len(values) < reg.SUMMARY_COUNT:
        raise ValueError(f"expected {reg.SUMMARY_COUNT} registers, got {len(values)}")
    return BatteryTelemetry(
        timestamp=time.time() if timestamp is None else timestamp,
        pack_voltage=values[reg.REG_PACK_VOLTAGE] * reg.SCALE_VOLTAGE,
        pack_current=reg.to_signed16(values[reg.REG_PACK_CURRENT]) * reg.SCALE_CURRENT,
        soc=values[reg.REG_SOC] * reg.SCALE_PERCENT,
        soh=values[reg.REG_SOH] * reg.SCALE_PERCENT,
        remaining_capacity=values[reg.REG_REMAINING_CAPACITY] * reg.SCALE_CAPACITY,
        cycle_count=values[reg.REG_CYCLE_COUNT],
        max_cell_mv=values[reg.REG_MAX_CELL_MV],
        min_cell_mv=values[reg.REG_MIN_CELL_MV],
        max_temp=reg.to_signed16(values[reg.REG_MAX_TEMP]) * reg.SCALE_TEMP,
        min_temp=reg.to_signed16(values[reg.REG_MIN_TEMP]) * reg.SCALE_TEMP,
        warnings=BatteryFlag(values[reg.REG_WARNING_FLAGS]),
        protections=BatteryFlag(values[reg.REG_PROTECTION_FLAGS]),
    )
