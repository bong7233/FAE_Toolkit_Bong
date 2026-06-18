"""Background reader: blocks on a transport and emits received bytes."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from fae_toolkit.core.transport import Transport


class RxReader(QObject):
    """Runs a read loop on a worker thread, emitting RX data and errors."""

    received = Signal(bytes)
    error = Signal(str)

    def __init__(self, transport: Transport, chunk: int = 4096, timeout: float = 0.2) -> None:
        super().__init__()
        self._transport = transport
        self._chunk = chunk
        self._timeout = timeout
        self._running = False

    @Slot()
    def start(self) -> None:
        self._running = True
        while self._running:
            try:
                data = self._transport.read(self._chunk, timeout=self._timeout)
            except Exception as exc:  # transport closed / peer dropped
                if self._running:
                    self.error.emit(f"{type(exc).__name__}: {exc}")
                return
            if data:
                self.received.emit(bytes(data))

    def stop(self) -> None:
        self._running = False
