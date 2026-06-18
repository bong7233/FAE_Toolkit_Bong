"""Hex/ASCII helpers for the communication tester's frame entry and monitor."""

from __future__ import annotations


def parse_hex(text: str) -> bytes:
    """Parse a user-typed hex string into bytes.

    Accepts spaced/comma-separated bytes ("01 03 00", "0x01,0x03") or a
    contiguous string ("010300"). Raises ``ValueError`` on malformed input.
    """
    cleaned = text.strip().replace(",", " ").replace("0x", " ").replace("0X", " ")
    parts = cleaned.split()
    if not parts:
        return b""
    if len(parts) == 1:
        token = parts[0]
        if len(token) % 2 != 0:
            raise ValueError("hex string must have an even number of digits")
        return bytes.fromhex(token)
    out = bytearray()
    for part in parts:
        if len(part) > 2:
            raise ValueError(f"'{part}' is not a single byte")
        out.append(int(part, 16))
    return bytes(out)


def to_hex(data: bytes) -> str:
    """Format bytes as space-separated uppercase hex ("01 03 0A")."""
    return " ".join(f"{b:02X}" for b in data)


def to_ascii(data: bytes) -> str:
    """Printable-ASCII view; non-printable bytes shown as '.'."""
    return "".join(chr(b) if 32 <= b < 127 else "." for b in data)
