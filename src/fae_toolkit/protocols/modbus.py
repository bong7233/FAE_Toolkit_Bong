"""Minimal Modbus-RTU client/server, implemented from scratch.

Many industrial BMS and remote-IO modules speak Modbus RTU over RS232/RS485.
Implementing the framing here (rather than depending on a library) keeps the
toolkit dependency-light and documents the exact bytes on the wire.

Supported function codes:

* ``0x01`` Read Coils                (digital outputs read-back)
* ``0x02`` Read Discrete Inputs      (digital inputs / sensors / PIO)
* ``0x03`` Read Holding Registers    (config / analog as 16-bit)
* ``0x04`` Read Input Registers      (analog inputs)
* ``0x05`` Write Single Coil         (set a digital output)
* ``0x06`` Write Single Register

Both the client helpers (used by the application) and :func:`process_request`
(used by the device simulators) share the same framing and CRC code.
"""

from __future__ import annotations

import struct

from fae_toolkit.core.crc import append_crc, check_crc
from fae_toolkit.core.transport import Transport, read_exact

READ_COILS = 0x01
READ_DISCRETE_INPUTS = 0x02
READ_HOLDING_REGISTERS = 0x03
READ_INPUT_REGISTERS = 0x04
WRITE_SINGLE_COIL = 0x05
WRITE_SINGLE_REGISTER = 0x06
_EXCEPTION_MASK = 0x80

_COIL_ON = 0xFF00
_COIL_OFF = 0x0000


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
# Bit packing helpers (coils / discrete inputs)
# --------------------------------------------------------------------------- #
def pack_bits(bits: list[bool]) -> bytes:
    """Pack booleans into bytes, LSB-first (Modbus coil order)."""
    out = bytearray((len(bits) + 7) // 8)
    for i, bit in enumerate(bits):
        if bit:
            out[i // 8] |= 1 << (i % 8)
    return bytes(out)


def unpack_bits(data: bytes, count: int) -> list[bool]:
    """Unpack *count* LSB-first booleans from *data*."""
    return [bool((data[i // 8] >> (i % 8)) & 1) for i in range(count)]


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
def _read_registers(
    transport: Transport, unit: int, func: int, start: int, count: int, timeout: float
) -> list[int]:
    transport.reset_input()
    transport.write(append_crc(struct.pack(">BBHH", unit, func, start, count)))

    header = read_exact(transport, 2, timeout)  # unit, function
    rfunc = header[1]
    if rfunc == (func | _EXCEPTION_MASK):
        rest = read_exact(transport, 3, timeout)
        if not check_crc(header + rest):
            raise ModbusError("CRC error in exception response")
        raise ModbusException.from_code(rest[0])
    if rfunc != func:
        raise ModbusError(f"unexpected function 0x{rfunc:02X}")
    if header[0] != unit:
        raise ModbusError(f"unexpected unit id {header[0]}")

    byte_count = read_exact(transport, 1, timeout)[0]
    if byte_count != count * 2:
        raise ModbusError(f"unexpected byte count {byte_count}")
    payload = read_exact(transport, byte_count + 2, timeout)  # data + CRC
    if not check_crc(header + bytes([byte_count]) + payload):
        raise ModbusError("CRC error in response")
    data = payload[:byte_count]
    return [struct.unpack_from(">H", data, i)[0] for i in range(0, byte_count, 2)]


def read_holding_registers(
    transport: Transport, unit: int, start: int, count: int, timeout: float = 1.0
) -> list[int]:
    """Read holding registers (function 0x03)."""
    return _read_registers(transport, unit, READ_HOLDING_REGISTERS, start, count, timeout)


def read_input_registers(
    transport: Transport, unit: int, start: int, count: int, timeout: float = 1.0
) -> list[int]:
    """Read input registers (function 0x04)."""
    return _read_registers(transport, unit, READ_INPUT_REGISTERS, start, count, timeout)


def _read_bits(
    transport: Transport, unit: int, func: int, start: int, count: int, timeout: float
) -> list[bool]:
    transport.reset_input()
    transport.write(append_crc(struct.pack(">BBHH", unit, func, start, count)))

    header = read_exact(transport, 2, timeout)
    rfunc = header[1]
    if rfunc == (func | _EXCEPTION_MASK):
        rest = read_exact(transport, 3, timeout)
        if not check_crc(header + rest):
            raise ModbusError("CRC error in exception response")
        raise ModbusException.from_code(rest[0])
    if rfunc != func:
        raise ModbusError(f"unexpected function 0x{rfunc:02X}")
    if header[0] != unit:
        raise ModbusError(f"unexpected unit id {header[0]}")

    byte_count = read_exact(transport, 1, timeout)[0]
    if byte_count != (count + 7) // 8:
        raise ModbusError(f"unexpected byte count {byte_count}")
    payload = read_exact(transport, byte_count + 2, timeout)
    if not check_crc(header + bytes([byte_count]) + payload):
        raise ModbusError("CRC error in response")
    return unpack_bits(payload[:byte_count], count)


def read_coils(
    transport: Transport, unit: int, start: int, count: int, timeout: float = 1.0
) -> list[bool]:
    """Read coils / digital outputs (function 0x01)."""
    return _read_bits(transport, unit, READ_COILS, start, count, timeout)


def read_discrete_inputs(
    transport: Transport, unit: int, start: int, count: int, timeout: float = 1.0
) -> list[bool]:
    """Read discrete inputs / sensors (function 0x02)."""
    return _read_bits(transport, unit, READ_DISCRETE_INPUTS, start, count, timeout)


def _write(transport: Transport, request: bytes, func: int, timeout: float) -> None:
    """Send a write request and validate the echo, handling exception replies."""
    transport.reset_input()
    transport.write(request)
    header = read_exact(transport, 2, timeout)  # unit, function
    if header[1] == (func | _EXCEPTION_MASK):
        rest = read_exact(transport, 3, timeout)  # exception code + CRC (5-byte reply)
        if not check_crc(header + rest):
            raise ModbusError("CRC error in exception response")
        raise ModbusException.from_code(rest[0])
    echo = header + read_exact(transport, 6, timeout)  # rest of the 8-byte echo
    if not check_crc(echo):
        raise ModbusError("CRC error in write response")
    if echo[:6] != request[:6]:
        raise ModbusError("write echo mismatch")


def write_single_register(
    transport: Transport, unit: int, address: int, value: int, timeout: float = 1.0
) -> None:
    """Write a single holding register (function 0x06)."""
    _write(
        transport, build_write_single_register(unit, address, value), WRITE_SINGLE_REGISTER, timeout
    )


def write_single_coil(
    transport: Transport, unit: int, address: int, on: bool, timeout: float = 1.0
) -> None:
    """Write a single coil / digital output (function 0x05)."""
    request = append_crc(
        struct.pack(">BBHH", unit, WRITE_SINGLE_COIL, address, _COIL_ON if on else _COIL_OFF)
    )
    _write(transport, request, WRITE_SINGLE_COIL, timeout)


# --------------------------------------------------------------------------- #
# Server side (used by device simulators)
# --------------------------------------------------------------------------- #
def request_length(function: int) -> int:
    """Expected on-the-wire length of a request frame for *function*."""
    if function in (
        READ_COILS,
        READ_DISCRETE_INPUTS,
        READ_HOLDING_REGISTERS,
        READ_INPUT_REGISTERS,
        WRITE_SINGLE_COIL,
        WRITE_SINGLE_REGISTER,
    ):
        return 8  # unit + func + 2x uint16 + CRC(2)
    return 0  # unknown


def process_request(
    frame: bytes,
    unit_id: int,
    *,
    read_holding=None,
    write_holding=None,
    read_input=None,
    read_coils=None,
    read_discrete=None,
    write_coil=None,
) -> bytes | None:
    """Process a request *frame* and return a response frame.

    Returns ``None`` when the frame is not addressed to *unit_id* or has a bad
    CRC (a real device would stay silent). Each ``read_*`` callback takes
    ``(start, count)``; register callbacks return ``list[int]`` and bit
    callbacks return ``list[bool]``. Callbacks may raise :class:`ModbusException`.
    """
    if len(frame) < 4 or not check_crc(frame):
        return None
    if frame[0] != unit_id:
        return None
    func = frame[1]
    try:
        if func in (READ_HOLDING_REGISTERS, READ_INPUT_REGISTERS):
            callback = read_holding if func == READ_HOLDING_REGISTERS else read_input
            if callback is None:
                raise IllegalFunction()
            _, _, start, count = struct.unpack(">BBHH", frame[:6])
            data = b"".join(struct.pack(">H", r & 0xFFFF) for r in callback(start, count))
            return append_crc(bytes([unit_id, func, len(data)]) + data)
        if func in (READ_COILS, READ_DISCRETE_INPUTS):
            callback = read_coils if func == READ_COILS else read_discrete
            if callback is None:
                raise IllegalFunction()
            _, _, start, count = struct.unpack(">BBHH", frame[:6])
            data = pack_bits(callback(start, count))
            return append_crc(bytes([unit_id, func, len(data)]) + data)
        if func == WRITE_SINGLE_REGISTER:
            if write_holding is None:
                raise IllegalFunction()
            _, _, address, value = struct.unpack(">BBHH", frame[:6])
            write_holding(address, value)
            return append_crc(frame[:6])
        if func == WRITE_SINGLE_COIL:
            if write_coil is None:
                raise IllegalFunction()
            _, _, address, value = struct.unpack(">BBHH", frame[:6])
            write_coil(address, value == _COIL_ON)
            return append_crc(frame[:6])
        raise IllegalFunction()
    except ModbusException as exc:
        return append_crc(bytes([unit_id, func | _EXCEPTION_MASK, exc.code]))


# --------------------------------------------------------------------------- #
# Frame decoding (used by the RX/TX monitor to annotate Modbus traffic)
# --------------------------------------------------------------------------- #
_FUNCTION_NAMES = {
    READ_COILS: "Read Coils",
    READ_DISCRETE_INPUTS: "Read Discrete Inputs",
    READ_HOLDING_REGISTERS: "Read Holding Registers",
    READ_INPUT_REGISTERS: "Read Input Registers",
    WRITE_SINGLE_COIL: "Write Single Coil",
    WRITE_SINGLE_REGISTER: "Write Single Register",
}

_EXCEPTION_NAMES = {
    0x01: "Illegal Function",
    0x02: "Illegal Data Address",
    0x03: "Illegal Data Value",
    0x04: "Slave Device Failure",
    0x05: "Acknowledge",
    0x06: "Slave Device Busy",
    0x08: "Memory Parity Error",
    0x0A: "Gateway Path Unavailable",
    0x0B: "Gateway Target Failed To Respond",
}


def describe_frame(data: bytes, response: bool = True) -> str:
    """Return a one-line human decode of a Modbus-RTU *frame*.

    Used by the monitor to annotate raw bytes. ``response`` selects the request
    vs. response interpretation for the read function codes (both directions
    share a function byte but carry different payloads). Returns ``""`` when the
    bytes are too short to be a Modbus frame.
    """
    if len(data) < 4:
        return ""
    crc_tag = "CRC OK" if check_crc(data) else "CRC BAD"
    unit = data[0]
    func = data[1]

    if func & _EXCEPTION_MASK:
        base = func & ~_EXCEPTION_MASK
        name = _FUNCTION_NAMES.get(base, f"0x{base:02X}")
        code = data[2] if len(data) >= 3 else 0
        exc = _EXCEPTION_NAMES.get(code, f"0x{code:02X}")
        return f"unit {unit}  EXCEPTION {name} -> {exc}  [{crc_tag}]"

    name = _FUNCTION_NAMES.get(func)
    if name is None:
        return f"unit {unit}  func 0x{func:02X}  [{crc_tag}]"

    kind = "RSP" if response else "REQ"
    try:
        detail = _describe_payload(func, data, response)
    except (struct.error, IndexError):
        detail = "(truncated)"
    sep = "  " if detail else ""
    return f"unit {unit}  {kind} {name}{sep}{detail}  [{crc_tag}]"


def _describe_payload(func: int, data: bytes, response: bool) -> str:
    """Decode the body of a (non-exception) Modbus frame into text."""
    if func in (WRITE_SINGLE_COIL, WRITE_SINGLE_REGISTER):
        # Requests and responses echo the same 4-byte body.
        _, _, addr, value = struct.unpack(">BBHH", data[:6])
        if func == WRITE_SINGLE_COIL:
            return f"addr={addr} -> {'ON' if value == _COIL_ON else 'OFF'}"
        return f"addr={addr} value={value} (0x{value:04X})"

    if not response:
        _, _, start, count = struct.unpack(">BBHH", data[:6])
        return f"start={start} count={count}"

    # Read responses: byte count then payload.
    byte_count = data[2]
    body = data[3 : 3 + byte_count]
    if func in (READ_HOLDING_REGISTERS, READ_INPUT_REGISTERS):
        regs = [struct.unpack_from(">H", body, i)[0] for i in range(0, len(body), 2)]
        return f"{len(regs)} regs {regs}"
    bits = unpack_bits(body, byte_count * 8)
    return f"{len(bits)} bits {[int(b) for b in bits]}"
