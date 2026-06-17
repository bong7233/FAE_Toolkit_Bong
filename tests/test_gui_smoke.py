"""Offscreen smoke test for the PySide6 GUI.

Skipped automatically when PySide6 is not installed (e.g. the headless test
job). Runs under the Qt 'offscreen' platform so it needs no display.
"""

import os
import time

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from fae_toolkit.ui.battery_view import SIM_LABEL  # noqa: E402
from fae_toolkit.ui.main_window import MainWindow  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_battery_view_updates_against_simulator(qapp):
    window = MainWindow()
    view = window.battery_view
    view.port_combo.setCurrentText(SIM_LABEL)
    view.interval_spin.setValue(100)
    view._connect()
    assert view._connected

    deadline = time.monotonic() + 5.0
    while view._values["pack_voltage"].text() == "—" and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.02)

    assert view._values["pack_voltage"].text() != "—"
    assert "NORMAL" in view.alarm_banner.text() or "ALARM" in view.alarm_banner.text()

    view.shutdown()
    assert not view._connected
