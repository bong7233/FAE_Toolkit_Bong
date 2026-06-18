"""Parity test: the C++ (pybind11) CRC must match the pure-Python one.

Skipped when the native module is not built, so the normal test-suite stays
green without a compiler. The CI pybind11 job builds the module and runs the
equivalent check.
"""

import pytest

from fae_toolkit.core import crc


@pytest.mark.skipif(not crc.HAS_NATIVE, reason="native faecore module not built")
def test_native_matches_python():
    for data in [b"", b"123456789", b"\x01\x03\x00\x00\x00\x0c", bytes(range(64))]:
        assert crc.crc16_modbus_native(data) == crc.crc16_modbus(data)
