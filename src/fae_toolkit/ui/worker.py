"""Background polling worker for the BMS view.

Runs in its own ``QThread`` and emits telemetry/errors as Qt signals so the GUI
thread is never blocked by serial I/O.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from fae_toolkit.protocols.bms import BmsClient
from fae_toolkit.protocols.bms.model import BatteryTelemetry


class BmsPollWorker(QObject):
    """Polls a :class:`BmsClient` on a timer and reports results via signals."""

    telemetry = Signal(BatteryTelemetry)
    error = Signal(str)

    def __init__(self, client: BmsClient, interval_ms: int = 500) -> None:
        super().__init__()
        self._client = client
        self._interval_ms = interval_ms
        self._timer: QTimer | None = None

    @Slot()
    def start(self) -> None:
        # Created here so the timer lives in the worker's own thread.
        self._timer = QTimer()
        self._timer.setInterval(self._interval_ms)
        self._timer.timeout.connect(self._poll)
        self._timer.start()

    @Slot()
    def stop(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None

    @Slot(int)
    def set_interval(self, interval_ms: int) -> None:
        self._interval_ms = interval_ms
        if self._timer is not None:
            self._timer.setInterval(interval_ms)

    def _poll(self) -> None:
        try:
            self.telemetry.emit(self._client.read_telemetry())
        except Exception as exc:  # surfaced in the UI, never crashes the worker
            self.error.emit(f"{type(exc).__name__}: {exc}")
