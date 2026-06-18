"""ROS-agnostic telemetry sources.

Thin wrappers that own a device client (a real serial port, or the built-in
simulator when no port is given) and expose a single ``read()`` call. The ROS 2
bridge nodes build on these, but the logic here has no ROS dependency and is
covered by the normal test-suite.
"""

from __future__ import annotations

from fae_toolkit.core.transport import SerialTransport, create_loopback_pair
from fae_toolkit.protocols.bms import BmsClient
from fae_toolkit.protocols.bms.model import BatteryTelemetry
from fae_toolkit.protocols.io import IoClient
from fae_toolkit.protocols.io.model import IoSnapshot
from fae_toolkit.sim.bms import BmsSimulator
from fae_toolkit.sim.io import IoSimulator


class BmsTelemetrySource:
    """Yields :class:`BatteryTelemetry`, from a real port or the simulator."""

    def __init__(self, port: str | None = None, unit_id: int = 1, timeout: float = 1.0) -> None:
        self._sim: BmsSimulator | None = None
        if port:
            self._transport = SerialTransport(port)
            self._transport.open()
        else:
            app_end, dev_end = create_loopback_pair()
            self._sim = BmsSimulator(dev_end, unit_id=unit_id)
            self._sim.start()
            self._transport = app_end
        self._client = BmsClient(self._transport, unit_id=unit_id, timeout=timeout)

    def read(self) -> BatteryTelemetry:
        return self._client.read_telemetry()

    def close(self) -> None:
        if self._sim is not None:
            self._sim.stop()
        self._transport.close()

    def __enter__(self) -> BmsTelemetrySource:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class IoTelemetrySource:
    """Yields :class:`IoSnapshot`, from a real port or the simulator."""

    def __init__(self, port: str | None = None, unit_id: int = 1, timeout: float = 1.0) -> None:
        self._sim: IoSimulator | None = None
        if port:
            self._transport = SerialTransport(port)
            self._transport.open()
        else:
            app_end, dev_end = create_loopback_pair()
            self._sim = IoSimulator(dev_end, unit_id=unit_id)
            self._sim.start()
            self._transport = app_end
        self._client = IoClient(self._transport, unit_id=unit_id, timeout=timeout)

    def read(self) -> IoSnapshot:
        return self._client.read_snapshot()

    def close(self) -> None:
        if self._sim is not None:
            self._sim.stop()
        self._transport.close()

    def __enter__(self) -> IoTelemetrySource:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
