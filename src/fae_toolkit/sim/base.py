"""Base class for Modbus-RTU device simulators.

Owns the background server loop (read request bytes off a transport, frame and
dispatch them, write the response) and the comm-level fault injection shared by
all device simulators. Subclasses supply the device physics (:meth:`_tick`) and
the per-function register handling (:meth:`_respond`).
"""

from __future__ import annotations

import threading
import time

from fae_toolkit.core.crc import check_crc
from fae_toolkit.core.transport import Transport

_REQUEST_LEN = 8  # every supported request (read/write) is 8 bytes on the wire


class ModbusDeviceSimulator:
    """Runs a Modbus-RTU server over a :class:`Transport` in a daemon thread."""

    def __init__(
        self, transport: Transport, unit_id: int = 1, *, poll_interval: float = 0.01
    ) -> None:
        self.transport = transport
        self.unit_id = unit_id
        self.poll_interval = poll_interval

        self._buffer = bytearray()
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_tick = time.monotonic()

        self._drop_responses = 0
        self._corrupt_next = False

    # --- lifecycle -------------------------------------------------------- #
    def start(self):
        if not self.transport.is_open:
            self.transport.open()
        self._stop.clear()
        self._last_tick = time.monotonic()
        self._thread = threading.Thread(target=self._run, name=type(self).__name__, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()

    # --- comm fault injection (thread-safe) ------------------------------- #
    def inject_comm_timeout(self, count: int = 1) -> None:
        """Drop the next *count* responses, simulating a comm timeout."""
        with self._lock:
            self._drop_responses += count

    def inject_crc_error(self) -> None:
        """Corrupt the CRC of the next response."""
        with self._lock:
            self._corrupt_next = True

    def clear_faults(self) -> None:
        with self._lock:
            self._drop_responses = 0
            self._corrupt_next = False

    # --- server loop ------------------------------------------------------ #
    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                data = self.transport.read(64, timeout=self.poll_interval)
            except RuntimeError:
                break  # transport closed
            now = time.monotonic()
            self._tick(now - self._last_tick)
            self._last_tick = now
            if data:
                self._buffer.extend(data)
                self._process_buffer()

    def _process_buffer(self) -> None:
        while len(self._buffer) >= _REQUEST_LEN:
            frame = bytes(self._buffer[:_REQUEST_LEN])
            if check_crc(frame):
                del self._buffer[:_REQUEST_LEN]
                response = self._respond(frame)
                if response is not None:
                    self._send(response)
            else:
                del self._buffer[0]  # resync on noise

    def _send(self, response: bytes) -> None:
        with self._lock:
            if self._drop_responses > 0:
                self._drop_responses -= 1
                return
            if self._corrupt_next:
                self._corrupt_next = False
                response = response[:-1] + bytes([response[-1] ^ 0xFF])
        self.transport.write(response)

    # --- subclass hooks --------------------------------------------------- #
    def _tick(self, dt: float) -> None:
        """Advance device physics by *dt* seconds (override as needed)."""

    def _respond(self, frame: bytes) -> bytes | None:
        """Return a response frame for a CRC-valid request (must override)."""
        raise NotImplementedError
