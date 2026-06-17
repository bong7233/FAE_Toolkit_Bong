"""Tests for the CRC-16/MODBUS implementation."""

from fae_toolkit.core.crc import append_crc, check_crc, crc16_modbus


def test_known_check_value():
    # Standard CRC-16/MODBUS catalogue check value for b"123456789".
    assert crc16_modbus(b"123456789") == 0x4B37


def test_append_and_check_roundtrip():
    frame = append_crc(b"\x01\x03\x00\x00\x00\x0c")
    assert len(frame) == 8
    assert check_crc(frame)


def test_check_detects_corruption():
    frame = bytearray(append_crc(b"\x01\x03\x00\x00\x00\x0c"))
    frame[2] ^= 0xFF  # flip a payload bit
    assert not check_crc(bytes(frame))


def test_crc_is_little_endian_on_wire():
    payload = b"\x01\x03\x00\x00\x00\x0c"
    crc = crc16_modbus(payload)
    frame = append_crc(payload)
    assert frame[-2] == (crc & 0xFF)
    assert frame[-1] == ((crc >> 8) & 0xFF)
