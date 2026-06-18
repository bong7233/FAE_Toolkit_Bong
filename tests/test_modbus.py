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


def test_pack_unpack_bits_roundtrip():
    bits = [True, False, True, True, False, False, False, True, True, False]
    packed = modbus.pack_bits(bits)
    assert len(packed) == 2  # ceil(10 / 8)
    assert modbus.unpack_bits(packed, len(bits)) == bits


def test_process_read_coils():
    bits = [True, False, True, False, True, True, False, False, True, True]
    request = modbus.append_crc(struct.pack(">BBHH", 1, modbus.READ_COILS, 0, len(bits)))
    response = modbus.process_request(request, 1, read_coils=lambda s, c: bits[s : s + c])
    assert response is not None
    assert response[1] == modbus.READ_COILS
    assert response[2] == 2
    assert check_crc(response)
    assert modbus.unpack_bits(response[3 : 3 + response[2]], len(bits)) == bits


def test_process_read_discrete_inputs_without_callback_is_exception():
    request = modbus.append_crc(struct.pack(">BBHH", 1, modbus.READ_DISCRETE_INPUTS, 0, 4))
    response = modbus.process_request(request, 1)
    assert response is not None
    assert response[1] == (modbus.READ_DISCRETE_INPUTS | 0x80)
    assert response[2] == modbus.IllegalFunction.code


def test_process_read_input_registers():
    request = modbus.append_crc(struct.pack(">BBHH", 1, modbus.READ_INPUT_REGISTERS, 0, 3))
    response = modbus.process_request(request, 1, read_input=lambda s, c: [10, 20, 30])
    assert response is not None
    assert response[1] == modbus.READ_INPUT_REGISTERS
    values = [struct.unpack_from(">H", response, 3 + 2 * i)[0] for i in range(3)]
    assert values == [10, 20, 30]


def test_process_write_single_coil():
    writes: dict[int, bool] = {}
    request = modbus.append_crc(struct.pack(">BBHH", 1, modbus.WRITE_SINGLE_COIL, 5, 0xFF00))
    response = modbus.process_request(
        request, 1, write_coil=lambda addr, on: writes.__setitem__(addr, on)
    )
    assert writes == {5: True}
    assert response == request


# --------------------------------------------------------------------------- #
# describe_frame (RX/TX monitor decoder)
# --------------------------------------------------------------------------- #
def test_describe_read_request():
    frame = modbus.build_read_holding_registers(unit=1, start=2, count=3)
    text = modbus.describe_frame(frame, response=False)
    assert "REQ" in text
    assert "Read Holding Registers" in text
    assert "start=2" in text and "count=3" in text
    assert "CRC OK" in text


def test_describe_read_response():
    response = modbus.process_request(
        modbus.build_read_holding_registers(unit=1, start=0, count=3),
        unit_id=1,
        read_holding=lambda s, c: [10, 20, 30],
    )
    text = modbus.describe_frame(response, response=True)
    assert "RSP" in text
    assert "[10, 20, 30]" in text
    assert "CRC OK" in text


def test_describe_coil_bits_response():
    bits = [True, False, True, True]
    response = modbus.process_request(
        modbus.append_crc(struct.pack(">BBHH", 1, modbus.READ_COILS, 0, len(bits))),
        unit_id=1,
        read_coils=lambda s, c: bits,
    )
    text = modbus.describe_frame(response, response=True)
    assert "Read Coils" in text
    assert "1, 0, 1, 1" in text


def test_describe_write_single_coil():
    frame = modbus.append_crc(struct.pack(">BBHH", 1, modbus.WRITE_SINGLE_COIL, 5, 0xFF00))
    text = modbus.describe_frame(frame, response=False)
    assert "Write Single Coil" in text
    assert "addr=5" in text and "ON" in text


def test_describe_exception_response():
    response = modbus.append_crc(
        bytes([1, modbus.READ_HOLDING_REGISTERS | 0x80, modbus.IllegalDataAddress.code])
    )
    text = modbus.describe_frame(response, response=True)
    assert "EXCEPTION" in text
    assert "Illegal Data Address" in text


def test_describe_bad_crc_flagged():
    frame = bytearray(modbus.build_read_holding_registers(unit=1, start=0, count=1))
    frame[-1] ^= 0xFF
    assert "CRC BAD" in modbus.describe_frame(bytes(frame), response=False)


def test_describe_too_short_returns_empty():
    assert modbus.describe_frame(b"\x01\x03", response=False) == ""
