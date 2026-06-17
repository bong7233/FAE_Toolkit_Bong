"""Minimal Modbus-RTU client/server, implemented from scratch.

Many industrial BMS and remote-IO modules speak Modbus RTU over RS232/RS485.
Implementing the framing here (rather than depending on a library) keeps the
toolkit dependency-light and documents the exact bytes on the wire.

Supported function codes:

* ``0x03`` Read Holding Registers
* ``0x06`` Write Single Register

Both the client helpers (used by the application) and :func:`process_request`
(used by the device simulators) share the same framing and CRC code.
"""

from __future__ import annotations

import struct

from fae_toolkit.core.crc import append_crc, check_crc
from fae_toolkit.core.transport import Transport, read_exact

READ_HOLDING_REGISTERS = 0x03
WRITE_SINGLE_REGISTER = 0x06
_EXCEPTION_MASK = 0x80


class ModbusError(Exception):
    """Framing/transport-level error detected by the client."""


class ModbusException(ModbusError):
    """A Modbus *exception response* reported by the device (func | 0x80)."""

    code: int = 0

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.__class__.__name__)

    @staticmethod
    def from_code(code: int) -> ModbusException:
        return _EXCEPTION_BY_CODE.get(code, _UnknownException)(f"exception code 0x{code:02X}")


class IllegalFunction(ModbusException):
    code = 0x01


class IllegalDataAddress(ModbusException):
    code = 0x02


class IllegalDataValue(ModbusException):
    code = 0x03


class _UnknownException(ModbusException):
    code = 0xFF


_EXCEPTION_BY_CODE = {
    cls.code: cls for cls in (IllegalFunction, IllegalDataAddress, IllegalDataValue)
}


# --------------------------------------------------------------------------- #
# Request builders (client side)
# --------------------------------------------------------------------------- #
def build_read_holding_registers(unit: int, start: int, count: int) -> bytes:
    if not 1 <= count <= 125:
        raise ValueError("count must be 1..125")
    return append_crc(struct.pack(">BBHH", unit, READ_HOLDING_REGISTERS, start, count))


def build_write_single_register(unit: int, address: int, value: int) -> bytes:
    return append_crc(struct.pack(">BBHH", unit, WRITE_SINGLE_REGISTER, address, value & 0xFFFF))


# --------------------------------------------------------------------------- #
# Client transactions
# --------------------------------------------------------------------------- #
def read_holding_registers(
    transport: Transport,
    unit: int,
    start: int,
    count: int,
    timeout: float = 1.0,
) -> list[int]:
    """Perform a Read-Holding-Registers transaction and return register values.

    Raises :class:`ModbusException` on a device exception response,
    :class:`ModbusError` on framing/CRC errors, and
    :class:`~fae_toolkit.core.transport.TransportTimeout` on no/short reply.
    """
    transport.reset_input()
    transport.write(build_read_holding_registers(unit, start, count))

    header = read_exact(transport, 2, timeout)  # unit, function
    func = header[1]
    if func == (READ_HOLDING_REGISTERS | _EXCEPTION_MASK):
        rest = read_exact(transport, 3, timeout)  # exception code + CRC
        if not check_crc(header + rest):
            raise ModbusError("CRC error in exception response")
        raise ModbusException.from_code(rest[0])
    if func != READ_HOLDING_REGISTERS:
        raise ModbusError(f"unexpected function 0x{func:02X}")
    if header[0] != unit:
        raise ModbusError(f"unexpected unit id {header[0]}")

    byte_count = read_exact(transport, 1, timeout)[0]
    if byte_count != count * 2:
        raise ModbusError(f"unexpected byte count {byte_count}")
    payload = read_exact(transport, byte_count + 2, timeout)  # data + CRC
    frame = header + bytes([byte_count]) + payload
    if not check_crc(frame):
        raise ModbusError("CRC error in response")
    data = payload[:byte_count]
    return [struct.unpack_from(">H", data, i)[0] for i in range(0, byte_count, 2)]


def write_single_register(
    transport: Transport,
    unit: int,
    address: int,
    value: int,
    timeout: float = 1.0,
) -> None:
    transport.reset_input()
    request = build_write_single_register(unit, address, value)
    transport.write(request)
    echo = read_exact(transport, 8, timeout)
    if not check_crc(echo):
        raise ModbusError("CRC error in write response")
    if echo[1] == (WRITE_SINGLE_REGISTER | _EXCEPTION_MASK):
        raise ModbusException.from_code(echo[2])
    if echo[:6] != request[:6]:
        raise ModbusError("write echo mismatch")


# --------------------------------------------------------------------------- #
# Server side (used by device simulators)
# --------------------------------------------------------------------------- #
def request_length(function: int) -> int:
    """Expected on-the-wire length of a request frame for *function*."""
    if function in (READ_HOLDING_REGISTERS, WRITE_SINGLE_REGISTER):
        return 8  # unit + func + 2x uint16 + CRC(2)
    return 0  # unknown


def process_request(
    frame: bytes,
    unit_id: int,
    *,
    read_holding,
    write_holding=None,
) -> bytes | None:
    """Process a request *frame* and return a response frame.

    Returns ``None`` when the frame is not addressed to *unit_id* or has a bad
    CRC (a real device would stay silent). ``read_holding(start, count)`` must
    return a list of register values and may raise :class:`ModbusException`.
    """
    if len(frame) < 4 or not check_crc(frame):
        return None
    if frame[0] != unit_id:
        return None
    func = frame[1]
    try:
        if func == READ_HOLDING_REGISTERS:
            _, _, start, count = struct.unpack(">BBHH", frame[:6])
            regs = read_holding(start, count)
            data = b"".join(struct.pack(">H", r & 0xFFFF) for r in regs)
            return append_crc(bytes([unit_id, func, len(data)]) + data)
        if func == WRITE_SINGLE_REGISTER:
            if write_holding is None:
                raise IllegalFunction()
            _, _, address, value = struct.unpack(">BBHH", frame[:6])
            write_holding(address, value)
            return append_crc(frame[:6])  # echo request back
        raise IllegalFunction()
    except ModbusException as exc:
        return append_crc(bytes([unit_id, func | _EXCEPTION_MASK, exc.code]))
