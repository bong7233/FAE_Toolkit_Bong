"""Verify the pybind11 `faecore` module matches the pure-Python implementation.

Run after building with -DFAE_BUILD_PYBIND=ON, with the build's py/ dir on the
PYTHONPATH. Used by the CI pybind11 job.
"""

import faecore

assert faecore.crc16_modbus(b"123456789") == 0x4B37, "CRC catalogue value mismatch"

frame = faecore.build_read_holding_registers(1, 0, 12)
assert frame.hex() == "01030000000c45cf", frame.hex()

print("pybind11 faecore OK:", frame.hex())
