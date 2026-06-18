"""Real serial-path test using a socat virtual serial pair.

Unlike the in-process loopback, this drives ``SerialTransport`` (pyserial)
against actual OS serial devices, so the real port code path is covered.
Skipped where pyserial or socat are unavailable (e.g. Windows).
"""

import os
import shutil
import subprocess
import sys
import time

import pytest

pytest.importorskip("serial")
if sys.platform.startswith("win") or shutil.which("socat") is None:
    pytest.skip("socat virtual serial pair is POSIX-only", allow_module_level=True)

from fae_toolkit.core.transport import SerialTransport  # noqa: E402
from fae_toolkit.protocols.bms import BmsClient  # noqa: E402
from fae_toolkit.sim.bms import BmsSimulator  # noqa: E402


@pytest.fixture
def serial_pair(tmp_path):
    a = str(tmp_path / "ttyA")
    b = str(tmp_path / "ttyB")
    proc = subprocess.Popen(
        ["socat", "-d", "-d", f"PTY,link={a},raw,echo=0", f"PTY,link={b},raw,echo=0"],
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(50):
            if os.path.islink(a) and os.path.islink(b):
                break
            time.sleep(0.1)
        else:
            pytest.skip("socat did not create the serial links")
        yield a, b
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_bms_telemetry_over_real_serial(serial_pair):
    dev_port, app_port = serial_pair
    dev = SerialTransport(dev_port, baudrate=115200)
    dev.open()
    sim = BmsSimulator(dev, poll_interval=0.005)
    sim.start()
    client = BmsClient(SerialTransport(app_port, baudrate=115200), timeout=2.0)
    client.transport.open()
    try:
        telemetry = client.read_telemetry()
        assert 14 * 3.0 < telemetry.pack_voltage < 14 * 4.2
        assert 0.0 <= telemetry.soc <= 100.0
    finally:
        sim.stop()
        client.transport.close()
        dev.close()
