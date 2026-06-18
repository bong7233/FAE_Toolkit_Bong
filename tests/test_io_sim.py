"""Integration tests: IO client talking to the IO simulator over loopback."""

import time

import pytest

from fae_toolkit.core.transport import TransportTimeout
from fae_toolkit.protocols import modbus
from fae_toolkit.protocols.io import io_map


def test_read_snapshot_shapes_and_defaults(io_link):
    _sim, client = io_link
    snap = client.read_snapshot()
    assert len(snap.di) == io_map.DI_COUNT
    assert len(snap.do) == io_map.DO_COUNT
    assert len(snap.ai) == io_map.AI_COUNT
    assert snap.interlock_ok  # safe by default
    assert snap.di[io_map.DI_ES] is True


def test_set_output_reads_back(io_link):
    _sim, client = io_link
    client.set_output(io_map.DO_LOAD_CLAMP, True)
    assert client.read_outputs()[io_map.DO_LOAD_CLAMP] is True


def test_light_tower_green_when_idle_and_safe(io_link):
    _sim, client = io_link
    outputs = client.read_outputs()
    assert outputs[io_map.DO_LAMP_GREEN] is True
    assert outputs[io_map.DO_LAMP_RED] is False


def test_interlock_refuses_motion_when_estop_tripped(io_link):
    sim, client = io_link
    sim.trip_estop(True)
    with pytest.raises(modbus.IllegalDataValue):
        client.set_output(io_map.DO_CONVEYOR, True)
    outputs = client.read_outputs()
    assert outputs[io_map.DO_LAMP_RED] is True
    assert outputs[io_map.DO_CONVEYOR] is False


def test_interlock_clears_and_allows_motion(io_link):
    sim, client = io_link
    sim.trip_estop(True)
    sim.clear_faults()
    client.set_output(io_map.DO_CONVEYOR, True)
    assert client.read_outputs()[io_map.DO_CONVEYOR] is True


def test_load_weight_rises_when_lifted(io_link):
    _sim, client = io_link
    client.set_output(io_map.DO_LOAD_CLAMP, True)
    client.set_output(io_map.DO_LIFT_UP, True)
    time.sleep(0.05)
    assert client.read_analog()[io_map.AI_WEIGHT] > 5.0


def test_injected_comm_timeout_then_recovers(io_link):
    sim, client = io_link
    client.timeout = 0.2
    sim.inject_comm_timeout(1)
    with pytest.raises(TransportTimeout):
        client.read_inputs()
    assert client.read_inputs()[io_map.DI_ES] is True


def test_illegal_address_raises(io_link):
    _sim, client = io_link
    with pytest.raises(modbus.IllegalDataAddress):
        modbus.read_discrete_inputs(client.transport, 1, 0, io_map.DI_COUNT + 5, timeout=0.5)
