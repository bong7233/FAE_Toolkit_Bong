"""Battery Management System (BMS) protocol layer.

Models a BMS that exposes telemetry as Modbus holding registers — the common
pattern documented in real BMS communication manuals. The register map, the
engineering-unit decoding, and a high-level client live here.
"""

from fae_toolkit.protocols.bms.client import BmsClient
from fae_toolkit.protocols.bms.model import BatteryFlag, BatteryTelemetry
from fae_toolkit.protocols.bms.registers import SUMMARY_COUNT, SUMMARY_START

__all__ = [
    "BmsClient",
    "BatteryTelemetry",
    "BatteryFlag",
    "SUMMARY_START",
    "SUMMARY_COUNT",
]
