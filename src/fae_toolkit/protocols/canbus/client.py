"""High-level CAN BMS client.

Reads broadcast frames off any python-can ``Bus`` (the bus is duck-typed, so
this module does not import ``can`` directly) and merges them into a state.
"""

from __future__ import annotations

import time

from fae_toolkit.core.transport import TransportTimeout
from fae_toolkit.protocols.bms.model import BatteryFlag
from fae_toolkit.protocols.canbus import frames
from fae_toolkit.protocols.canbus.model import CanBmsState


class CanBmsClient:
    def __init__(self, bus, timeout: float = 1.0) -> None:
        self.bus = bus
        self.timeout = timeout

    def read_state(self) -> CanBmsState:
        """Return the most recent telemetry, draining any backlog.

        Broadcast frames queue up, so we drain to the newest A/B rather than
        report stale values. Raises :class:`TransportTimeout` if nothing arrives.
        """
        deadline = time.monotonic() + self.timeout
        telem_a: tuple[float, float, float] | None = None
        telem_b: tuple[float, float, BatteryFlag] | None = None

        # Block for the first frame, then drain everything already queued.
        msg = self.bus.recv(timeout=self.timeout)
        while msg is not None:
            if msg.arbitration_id == frames.CAN_ID_TELEM_A:
                telem_a = frames.decode_telem_a(msg.data)
            elif msg.arbitration_id == frames.CAN_ID_TELEM_B:
                telem_b = frames.decode_telem_b(msg.data)
            msg = self.bus.recv(timeout=0.0)

        # If we only saw a B frame, wait briefly for the next A (voltage/SOC).
        while telem_a is None and time.monotonic() < deadline:
            msg = self.bus.recv(timeout=max(0.0, deadline - time.monotonic()))
            if msg is None:
                break
            if msg.arbitration_id == frames.CAN_ID_TELEM_A:
                telem_a = frames.decode_telem_a(msg.data)
            elif msg.arbitration_id == frames.CAN_ID_TELEM_B:
                telem_b = frames.decode_telem_b(msg.data)

        if telem_a is None:
            raise TransportTimeout("no CAN BMS telemetry received")

        voltage, current, soc = telem_a
        max_temp, min_temp, warnings = telem_b if telem_b else (0.0, 0.0, BatteryFlag(0))
        return CanBmsState(
            voltage=voltage,
            current=current,
            soc=soc,
            max_temp=max_temp,
            min_temp=min_temp,
            warnings=warnings,
        )
