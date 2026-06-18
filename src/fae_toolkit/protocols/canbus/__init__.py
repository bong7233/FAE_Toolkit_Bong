"""CAN-bus BMS protocol layer.

Many battery packs broadcast telemetry as periodic CAN frames rather than over
a request/response serial bus. This package decodes such broadcasts; the
simulator (:mod:`fae_toolkit.sim.can_bms`) and tests use python-can's in-process
``virtual`` bus, so no CAN hardware is required.
"""

from fae_toolkit.protocols.canbus import frames
from fae_toolkit.protocols.canbus.client import CanBmsClient
from fae_toolkit.protocols.canbus.model import CanBmsState

__all__ = ["frames", "CanBmsClient", "CanBmsState"]
