"""Tests for the telemetry CSV logger."""

import csv

from fae_toolkit.protocols.bms.model import BatteryFlag, BatteryTelemetry
from fae_toolkit.services.csv_logger import FIELDS, CsvLogger


def _telemetry() -> BatteryTelemetry:
    return BatteryTelemetry(
        timestamp=1_700_000_000.0,
        pack_voltage=53.2,
        pack_current=-20.0,
        soc=85.0,
        soh=98.0,
        remaining_capacity=42.5,
        cycle_count=10,
        max_cell_mv=3810,
        min_cell_mv=3790,
        max_temp=27.0,
        min_temp=25.0,
        warnings=BatteryFlag.OVER_TEMP,
    )


def test_csv_logger_writes_header_and_rows(tmp_path):
    path = tmp_path / "out.csv"
    with CsvLogger(path) as logger:
        logger.write(_telemetry())
        logger.write(_telemetry())
        assert logger.rows == 2

    with open(path, encoding="utf-8") as fh:
        rows = list(csv.reader(fh))

    assert rows[0] == FIELDS
    assert len(rows) == 3  # header + 2 data rows
    assert "OVER_TEMP" in rows[1][FIELDS.index("warnings")]
    assert rows[1][FIELDS.index("pack_voltage_V")] == "53.20"
