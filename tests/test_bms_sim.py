"""Integration tests: BMS client talking to the simulator over a loopback link.

These exercise the full encode -> transport -> decode path with no hardware.
"""

import time

import pytest

from fae_toolkit.core.transport import TransportTimeout
from fae_toolkit.protocols import modbus
from fae_toolkit.protocols.bms import BatteryFlag
from fae_toolkit.protocols.bms import registers as reg


def test_read_telemetry_plausible(bms_link):
    _sim, client = bms_link
    tel = client.read_telemetry()
    assert 14 * 3.0 < tel.pack_voltage < 14 * 4.2
    assert 0.0 <= tel.soc <= 100.0
    assert 0.0 <= tel.soh <= 100.0
    assert tel.pack_current < 0.0  # default load is a discharge
    assert tel.min_temp <= tel.max_temp
    assert tel.cell_delta_mv >= 0


def test_soc_decreases_under_discharge(bms_link):
    sim, client = bms_link
    sim.set_load_current(-400.0)
    first = client.read_telemetry().soc
    time.sleep(0.8)
    second = client.read_telemetry().soc
    assert second < first


def test_cell_voltages_read(bms_link):
    _sim, client = bms_link
    cells = client.read_cell_voltages(14)
    assert len(cells) == 14
    assert all(2500 < mv < 4300 for mv in cells)


def test_injected_comm_timeout_then_recovers(bms_link):
    sim, client = bms_link
    client.timeout = 0.2
    sim.inject_comm_timeout(1)
    with pytest.raises(TransportTimeout):
        client.read_telemetry()
    assert client.read_telemetry().pack_voltage > 0  # next request succeeds


def test_injected_crc_error_then_recovers(bms_link):
    sim, client = bms_link
    sim.inject_crc_error()
    with pytest.raises(modbus.ModbusError):
        client.read_telemetry()
    assert client.read_telemetry().pack_voltage > 0


def test_forced_warning_flag(bms_link):
    sim, client = bms_link
    sim.force_warning(BatteryFlag.OVER_TEMP)
    tel = client.read_telemetry()
    assert BatteryFlag.OVER_TEMP in tel.warnings
    assert tel.has_alarm
    assert "OVER_TEMP" in tel.active_flags()


def test_illegal_address_raises(bms_link):
    _sim, client = bms_link
    with pytest.raises(modbus.IllegalDataAddress):
        modbus.read_holding_registers(client.transport, 1, reg.REGISTER_SPAN + 10, 2, timeout=0.5)
