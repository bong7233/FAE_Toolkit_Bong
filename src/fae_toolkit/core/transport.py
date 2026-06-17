"""Transport abstraction for byte-stream device communication.

Two implementations are provided:

* :class:`SerialTransport` — a thin wrapper over ``pyserial`` for real
  RS232/RS485 ports (and virtual COM pairs created by ``socat``/``com0com``).
* :class:`LoopbackTransport` — an in-process, thread-safe byte pipe used to
  connect the device simulator to the application **without any hardware**, so
  the full encode → transport → decode path runs in tests, CI and demos.

Both expose the same minimal interface, so application code never knows whether
it is talking to a real port or a simulator.
"""

from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod


class TransportTimeout(TimeoutError):
    """Raised when the requested number of bytes did not arrive in time."""


class Transport(ABC):
    """Minimal byte-stream transport interface."""

    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def write(self, data: bytes) -> int:
        """Write *data*; return the number of bytes written."""

    @abstractmethod
    def read(self, size: int, timeout: float | None = None) -> bytes:
        """Read up to *size* bytes, blocking at most *timeout* seconds.

        Returns fewer than *size* bytes (possibly empty) if *timeout* elapses,
        mirroring ``pyserial`` semantics.
        """

    @property
    @abstractmethod
    def is_open(self) -> bool: ...

    def reset_input(self) -> None:  # noqa: B027 - optional hook, default no-op
        """Discard any buffered inbound bytes (best effort)."""

    def __enter__(self) -> Transport:
        self.open()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def read_exact(transport: Transport, size: int, timeout: float | None = None) -> bytes:
    """Read exactly *size* bytes or raise :class:`TransportTimeout`.

    Accumulates across multiple reads until *size* bytes arrive or the overall
    *timeout* budget is exhausted.
    """
    deadline = None if timeout is None else time.monotonic() + timeout
    buf = bytearray()
    while len(buf) < size:
        remaining = None if deadline is None else deadline - time.monotonic()
        if remaining is not None and remaining <= 0:
            break
        chunk = transport.read(size - len(buf), timeout=remaining)
        if chunk:
            buf.extend(chunk)
    if len(buf) < size:
        raise TransportTimeout(f"expected {size} bytes, received {len(buf)} before timeout")
    return bytes(buf)


class SerialTransport(Transport):
    """``pyserial``-backed transport for real (or virtual) serial ports."""

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        *,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: float = 1,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self._serial = None  # lazily created pyserial.Serial

    def open(self) -> None:
        import serial  # imported lazily so headless tests need no real port

        if self._serial is not None and self._serial.is_open:
            return
        self._serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=self.bytesize,
            parity=self.parity,
            stopbits=self.stopbits,
            timeout=0,  # per-read timeout is applied dynamically
        )

    def close(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    @property
    def is_open(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def reset_input(self) -> None:
        if self._serial is not None:
            self._serial.reset_input_buffer()

    def write(self, data: bytes) -> int:
        if self._serial is None:
            raise RuntimeError("serial port is not open")
        return self._serial.write(data) or 0

    def read(self, size: int, timeout: float | None = None) -> bytes:
        if self._serial is None:
            raise RuntimeError("serial port is not open")
        self._serial.timeout = timeout
        return self._serial.read(size)


class _BytePipe:
    """A thread-safe one-directional byte stream with blocking reads."""

    def __init__(self) -> None:
        self._buf = bytearray()
        self._cond = threading.Condition()
        self._closed = False

    def write(self, data: bytes) -> None:
        with self._cond:
            if self._closed:
                raise RuntimeError("pipe is closed")
            self._buf.extend(data)
            self._cond.notify_all()

    def read(self, size: int, timeout: float | None) -> bytes:
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._cond:
            while len(self._buf) < size and not self._closed:
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    break
                self._cond.wait(remaining)
            n = min(size, len(self._buf))
            out = bytes(self._buf[:n])
            del self._buf[:n]
            return out

    def clear(self) -> None:
        with self._cond:
            self._buf.clear()

    def close(self) -> None:
        with self._cond:
            self._closed = True
            self._cond.notify_all()


class LoopbackTransport(Transport):
    """In-process transport. Reads from one pipe and writes to another.

    Create connected endpoints with :func:`create_loopback_pair`.
    """

    def __init__(self, rx: _BytePipe, tx: _BytePipe) -> None:
        self._rx = rx
        self._tx = tx
        self._open = True

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    @property
    def is_open(self) -> bool:
        return self._open

    def reset_input(self) -> None:
        self._rx.clear()

    def write(self, data: bytes) -> int:
        if not self._open:
            raise RuntimeError("transport is closed")
        self._tx.write(bytes(data))
        return len(data)

    def read(self, size: int, timeout: float | None = None) -> bytes:
        if not self._open:
            raise RuntimeError("transport is closed")
        return self._rx.read(size, timeout)


def create_loopback_pair() -> tuple[LoopbackTransport, LoopbackTransport]:
    """Return two cross-connected :class:`LoopbackTransport` endpoints.

    Bytes written to one endpoint can be read from the other, modelling a
    null-modem cable between an application and a device simulator.
    """
    a2b = _BytePipe()
    b2a = _BytePipe()
    end_a = LoopbackTransport(rx=b2a, tx=a2b)
    end_b = LoopbackTransport(rx=a2b, tx=b2a)
    return end_a, end_b
