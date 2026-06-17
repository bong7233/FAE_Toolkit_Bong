"""Append battery telemetry to a CSV file (engineering units).

Deliberately Qt-free so it can be used from the GUI, the CLI, or tests.
"""

from __future__ import annotations

import csv
import datetime as _dt
from pathlib import Path

from fae_toolkit.protocols.bms.model import BatteryTelemetry

FIELDS = [
    "timestamp",
    "iso_time",
    "pack_voltage_V",
    "pack_current_A",
    "soc_pct",
    "soh_pct",
    "power_W",
    "max_temp_C",
    "min_temp_C",
    "cell_delta_mV",
    "warnings",
    "protections",
]


class CsvLogger:
    """Streaming CSV writer for :class:`BatteryTelemetry` rows."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._fh = self.path.open("w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._fh)
        self._writer.writerow(FIELDS)
        self.rows = 0

    def write(self, tel: BatteryTelemetry) -> None:
        iso = _dt.datetime.fromtimestamp(tel.timestamp).isoformat(timespec="milliseconds")
        self._writer.writerow(
            [
                f"{tel.timestamp:.3f}",
                iso,
                f"{tel.pack_voltage:.2f}",
                f"{tel.pack_current:.2f}",
                f"{tel.soc:.1f}",
                f"{tel.soh:.1f}",
                f"{tel.power:.1f}",
                f"{tel.max_temp:.1f}",
                f"{tel.min_temp:.1f}",
                tel.cell_delta_mv,
                "|".join(tel.warnings.labels()),
                "|".join(tel.protections.labels()),
            ]
        )
        self._fh.flush()
        self.rows += 1

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> CsvLogger:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
