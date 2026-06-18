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


def _pump_until(qapp, predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.02)


def test_battery_view_updates_against_simulator(qapp):
    window = MainWindow()
    view = window.battery_view
    view.port_combo.setCurrentText(SIM_LABEL)
    view.interval_spin.setValue(100)
    view._connect()
    assert view._connected

    _pump_until(qapp, lambda: view._values["pack_voltage"].text() != "—")

    assert view._values["pack_voltage"].text() != "—"
    assert "NORMAL" in view.alarm_banner.text() or "ALARM" in view.alarm_banner.text()

    view.shutdown()
    assert not view._connected


def test_io_view_updates_against_simulator(qapp):
    window = MainWindow()
    view = window.io_view
    view.port_combo.setCurrentText(SIM_LABEL)
    view.interval_spin.setValue(100)
    view._connect()
    assert view._connected

    _pump_until(qapp, lambda: view._ai_labels[0].text() != "—")

    assert view._ai_labels[0].text() != "—"
    assert "INTERLOCK" in view.interlock_banner.text()

    view.shutdown()
    assert not view._connected
