"""Tests for the Modbus-RTU framing (client builders + server processing)."""

import struct

import pytest

from fae_toolkit.core.crc import check_crc
from fae_toolkit.protocols import modbus


def test_build_read_request_is_valid_frame():
    frame = modbus.build_read_holding_registers(unit=1, start=0, count=12)
    assert len(frame) == 8
    assert frame[0] == 1
    assert frame[1] == modbus.READ_HOLDING_REGISTERS
    assert check_crc(frame)


def test_build_read_request_rejects_bad_count():
    with pytest.raises(ValueError):
        modbus.build_read_holding_registers(unit=1, start=0, count=0)


def test_process_read_request_roundtrip():
    request = modbus.build_read_holding_registers(unit=1, start=2, count=3)
    response = modbus.process_request(
        request, unit_id=1, read_holding=lambda start, count: list(range(start, start + count))
    )
    assert response is not None
    assert response[0] == 1
    assert response[1] == modbus.READ_HOLDING_REGISTERS
    assert response[2] == 6  # byte count = 2 * 3
    assert check_crc(response)
    data = response[3:-2]
    values = [struct.unpack_from(">H", data, i)[0] for i in range(0, len(data), 2)]
    assert values == [2, 3, 4]


def test_process_request_wrong_unit_is_silent():
    request = modbus.build_read_holding_registers(unit=2, start=0, count=1)
    assert modbus.process_request(request, unit_id=1, read_holding=lambda s, c: [0]) is None


def test_process_request_bad_crc_is_silent():
    request = bytearray(modbus.build_read_holding_registers(unit=1, start=0, count=1))
    request[-1] ^= 0xFF
    assert modbus.process_request(bytes(request), unit_id=1, read_holding=lambda s, c: [0]) is None


def test_process_request_reports_exception():
    def bad_read(start, count):
        raise modbus.IllegalDataAddress()

    request = modbus.build_read_holding_registers(unit=1, start=999, count=1)
    response = modbus.process_request(request, unit_id=1, read_holding=bad_read)
    assert response is not None
    assert response[1] == (modbus.READ_HOLDING_REGISTERS | 0x80)
    assert response[2] == modbus.IllegalDataAddress.code
    assert check_crc(response)


def test_process_write_single_register():
    written = {}
    request = modbus.build_write_single_register(unit=1, address=5, value=0x1234)
    response = modbus.process_request(
        request,
        unit_id=1,
        read_holding=lambda s, c: [],
        write_holding=lambda addr, val: written.__setitem__(addr, val),
    )
    assert written == {5: 0x1234}
    assert response == request  # write echoes the request


def test_exception_from_code():
    assert isinstance(modbus.ModbusException.from_code(0x02), modbus.IllegalDataAddress)
    assert isinstance(modbus.ModbusException.from_code(0x99), modbus.ModbusException)
