"""Smoke tests for the headless CLI entry point."""

from fae_toolkit.cli import main


def test_bms_demo_runs_against_simulator(capsys):
    rc = main(["bms-demo", "--duration", "1", "--interval", "0.1"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "simulator" in out
    assert "done" in out


def test_no_command_prints_help():
    assert main([]) == 0
