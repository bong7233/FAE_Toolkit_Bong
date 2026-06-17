"""Core infrastructure: transport abstraction and protocol primitives."""

from fae_toolkit.core.crc import crc16_modbus
from fae_toolkit.core.transport import (
    LoopbackTransport,
    SerialTransport,
    Transport,
    TransportTimeout,
    create_loopback_pair,
    read_exact,
)

__all__ = [
    "Transport",
    "SerialTransport",
    "LoopbackTransport",
    "TransportTimeout",
    "create_loopback_pair",
    "read_exact",
    "crc16_modbus",
]
