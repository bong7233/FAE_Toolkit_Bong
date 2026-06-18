"""Tests for the ROS-agnostic telemetry sources used by the ROS 2 bridge."""

from fae_toolkit.bridge import BmsTelemetrySource, IoTelemetrySource


def test_bms_source_reads_from_simulator():
    with BmsTelemetrySource() as source:
        telemetry = source.read()
    assert telemetry.pack_voltage > 0
    assert 0.0 <= telemetry.soc <= 100.0


def test_io_source_reads_from_simulator():
    with IoTelemetrySource() as source:
        snapshot = source.read()
    assert len(snapshot.di) > 0
    assert snapshot.interlock_ok  # safe by default
