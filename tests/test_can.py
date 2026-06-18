"""CAN BMS tests over python-can's in-process virtual bus (no hardware)."""

import time

import pytest

can = pytest.importorskip("can")

from fae_toolkit.core.transport import TransportTimeout  # noqa: E402
from fae_toolkit.protocols.bms.model import BatteryFlag  # noqa: E402
from fae_toolkit.protocols.canbus import CanBmsClient, frames  # noqa: E402
from fae_toolkit.sim.can_bms import CanBmsSimulator  # noqa: E402


def test_frame_roundtrip():
    data = frames.encode_telem_a(53.21, -20.0, 84.9)
    voltage, current, soc = frames.decode_telem_a(data)
    assert round(voltage, 2) == 53.21
    assert round(current, 2) == -20.0
    assert round(soc, 1) == 84.9

    data_b = frames.encode_telem_b(27.0, 25.0, BatteryFlag.OVER_TEMP)
    max_temp, min_temp, warnings = frames.decode_telem_b(data_b)
    assert round(max_temp, 1) == 27.0
    assert round(min_temp, 1) == 25.0
    assert BatteryFlag.OVER_TEMP in warnings


@pytest.fixture
def can_link():
    channel = "fae_test"
    dev_bus = can.Bus(interface="virtual", channel=channel, receive_own_messages=False)
    app_bus = can.Bus(interface="virtual", channel=channel, receive_own_messages=False)
    sim = CanBmsSimulator(dev_bus, period=0.02)
    sim.start()
    client = CanBmsClient(app_bus, timeout=1.0)
    try:
        yield sim, client
    finally:
        sim.stop()
        app_bus.shutdown()
        dev_bus.shutdown()


def test_read_state_plausible(can_link):
    _sim, client = can_link
    state = client.read_state()
    assert 14 * 3.0 < state.voltage < 14 * 4.2
    assert state.current < 0.0
    assert 0.0 <= state.soc <= 100.0


def test_forced_warning_visible(can_link):
    sim, client = can_link
    sim.force_warning(BatteryFlag.OVER_TEMP)
    time.sleep(0.05)
    state = client.read_state()
    assert state.has_alarm
    assert "OVER_TEMP" in state.active_flags()


def test_timeout_when_no_traffic():
    app_bus = can.Bus(interface="virtual", channel="fae_silent", receive_own_messages=False)
    client = CanBmsClient(app_bus, timeout=0.2)
    try:
        with pytest.raises(TransportTimeout):
            client.read_state()
    finally:
        app_bus.shutdown()
