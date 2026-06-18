"""CAN frame layout for the simulated BMS (two periodic broadcast frames)."""

from __future__ import annotations

import struct

from fae_toolkit.protocols.bms.model import BatteryFlag

CAN_ID_TELEM_A = 0x180  # voltage, current, SOC
CAN_ID_TELEM_B = 0x181  # max/min temperature, warning flags

_SCALE_V = 0.01
_SCALE_A = 0.01
_SCALE_PCT = 0.1
_SCALE_T = 0.1
_PAD2 = b"\x00\x00"


def encode_telem_a(voltage: float, current: float, soc: float) -> bytes:
    return (
        struct.pack(
            ">HhH",
            round(voltage / _SCALE_V),
            round(current / _SCALE_A),
            round(soc / _SCALE_PCT),
        )
        + _PAD2
    )


def decode_telem_a(data: bytes) -> tuple[float, float, float]:
    voltage, current, soc = struct.unpack_from(">HhH", data, 0)
    return voltage * _SCALE_V, current * _SCALE_A, soc * _SCALE_PCT


def encode_telem_b(max_temp: float, min_temp: float, warnings: BatteryFlag) -> bytes:
    return (
        struct.pack(">hhH", round(max_temp / _SCALE_T), round(min_temp / _SCALE_T), int(warnings))
        + _PAD2
    )


def decode_telem_b(data: bytes) -> tuple[float, float, BatteryFlag]:
    max_temp, min_temp, warnings = struct.unpack_from(">hhH", data, 0)
    return max_temp * _SCALE_T, min_temp * _SCALE_T, BatteryFlag(warnings)
