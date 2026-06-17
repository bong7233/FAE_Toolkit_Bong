"""BMS Modbus holding-register map and scaling factors.

The layout mirrors a typical BMS manual: a contiguous *summary* block with the
pack-level values, followed by per-cell voltages and temperature sensors.

All registers are 16-bit. Scaling converts raw register values to engineering
units (e.g. pack voltage is transmitted in 10 mV steps).
"""

from __future__ import annotations

# --- Summary block (0x0000 .. 0x000B) ------------------------------------- #
SUMMARY_START = 0x0000
SUMMARY_COUNT = 12

REG_PACK_VOLTAGE = 0x0000  # uint16, 0.01 V
REG_PACK_CURRENT = 0x0001  # int16,  0.01 A  (+charge / -discharge)
REG_SOC = 0x0002  # uint16, 0.1 %
REG_SOH = 0x0003  # uint16, 0.1 %
REG_REMAINING_CAPACITY = 0x0004  # uint16, 0.01 Ah
REG_CYCLE_COUNT = 0x0005  # uint16
REG_MAX_CELL_MV = 0x0006  # uint16, mV
REG_MIN_CELL_MV = 0x0007  # uint16, mV
REG_MAX_TEMP = 0x0008  # int16, 0.1 C
REG_MIN_TEMP = 0x0009  # int16, 0.1 C
REG_WARNING_FLAGS = 0x000A  # uint16 bitfield
REG_PROTECTION_FLAGS = 0x000B  # uint16 bitfield

# --- Per-cell / per-sensor blocks ----------------------------------------- #
CELL_VOLTAGES_START = 0x0010  # uint16 each, mV
MAX_CELLS = 16
TEMPS_START = 0x0020  # int16 each, 0.1 C
MAX_TEMPS = 4

# Total addressable register span served by the simulator.
REGISTER_SPAN = TEMPS_START + MAX_TEMPS

# --- Scaling factors ------------------------------------------------------- #
SCALE_VOLTAGE = 0.01
SCALE_CURRENT = 0.01
SCALE_PERCENT = 0.1
SCALE_CAPACITY = 0.01
SCALE_TEMP = 0.1


def to_signed16(value: int) -> int:
    """Interpret an unsigned 16-bit register as a signed int16."""
    return value - 0x10000 if value >= 0x8000 else value


def to_unsigned16(value: int) -> int:
    """Clamp/convert a signed value into an unsigned 16-bit register."""
    return value & 0xFFFF
