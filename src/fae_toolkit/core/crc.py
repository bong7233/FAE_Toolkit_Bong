"""CRC-16/MODBUS implementation.

Used by the Modbus-RTU framing in :mod:`fae_toolkit.protocols.modbus`.
Implemented from scratch (rather than pulling in a library) to demonstrate
the on-the-wire framing that real BMS/IO devices use.
"""

from __future__ import annotations

# Precomputed table for CRC-16/MODBUS (polynomial 0xA001, the reflected 0x8005).
_TABLE: list[int] = []
for _byte in range(256):
    _crc = _byte
    for _ in range(8):
        if _crc & 0x0001:
            _crc = (_crc >> 1) ^ 0xA001
        else:
            _crc >>= 1
    _TABLE.append(_crc)


def crc16_modbus(data: bytes) -> int:
    """Return the CRC-16/MODBUS checksum of *data* (init 0xFFFF)."""
    crc = 0xFFFF
    for byte in data:
        crc = (crc >> 8) ^ _TABLE[(crc ^ byte) & 0xFF]
    return crc


def append_crc(data: bytes) -> bytes:
    """Append the little-endian CRC-16/MODBUS to *data* (Modbus wire order)."""
    crc = crc16_modbus(data)
    return data + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def check_crc(frame: bytes) -> bool:
    """Return True if the last two bytes of *frame* are a valid Modbus CRC."""
    if len(frame) < 3:
        return False
    body, lo, hi = frame[:-2], frame[-2], frame[-1]
    crc = crc16_modbus(body)
    return (crc & 0xFF) == lo and ((crc >> 8) & 0xFF) == hi


# Optional native fast path: if the compiled C++ module (cpp/, built via
# pybind11) is importable, expose it. The pure-Python implementation above
# stays the default, so the toolkit always works without a compiler.
try:
    import faecore as _faecore

    HAS_NATIVE = True
except ImportError:  # pragma: no cover - native module is optional
    _faecore = None
    HAS_NATIVE = False


def crc16_modbus_native(data: bytes) -> int:
    """CRC-16/MODBUS via the compiled C++ module (raises if not built)."""
    if _faecore is None:
        raise RuntimeError("native faecore module is not available")
    return _faecore.crc16_modbus(bytes(data))
