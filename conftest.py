"""Pytest bootstrap: make ``src/`` importable and provide shared fixtures.

This lets the test-suite run straight from a checkout (``pytest``) without an
editable install, while still working after ``pip install -e .`` in CI.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

_SRC = pathlib.Path(__file__).parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from fae_toolkit.core.transport import create_loopback_pair  # noqa: E402
from fae_toolkit.protocols.bms import BmsClient  # noqa: E402
from fae_toolkit.sim.bms import BmsSimulator  # noqa: E402


@pytest.fixture
def bms_link():
    """Yield a (simulator, client) pair connected over an in-process link."""
    app_end, dev_end = create_loopback_pair()
    sim = BmsSimulator(dev_end, poll_interval=0.005)
    sim.start()
    client = BmsClient(app_end, timeout=0.5)
    try:
        yield sim, client
    finally:
        sim.stop()
