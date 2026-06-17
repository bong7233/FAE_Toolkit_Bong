"""Headless command-line entry point.

Runs the toolkit without any display, which makes it usable for automation and
as a CI smoke test. The ``bms-demo`` command talks to the built-in BMS
simulator (or a real serial port via ``--port``) and prints live telemetry,
injecting fault scenarios to show how comm errors and alarms are handled.
"""

from __future__ import annotations

import argparse
import sys
import time

from fae_toolkit import __version__
from fae_toolkit.core.transport import SerialTransport, TransportTimeout, create_loopback_pair
from fae_toolkit.protocols.bms import BatteryFlag, BmsClient
from fae_toolkit.protocols.modbus import ModbusError
from fae_toolkit.sim.bms import BmsSimulator


def _format_row(elapsed: float, tel) -> str:
    status = "OK" if not tel.has_alarm else "ALARM: " + ", ".join(tel.active_flags())
    return (
        f"t={elapsed:5.1f}s  "
        f"V={tel.pack_voltage:6.2f}  "
        f"I={tel.pack_current:+7.2f}A  "
        f"SOC={tel.soc:5.1f}%  "
        f"P={tel.power:+7.0f}W  "
        f"T={tel.max_temp:4.1f}C  "
        f"Δcell={tel.cell_delta_mv:3d}mV  "
        f"[{status}]"
    )


def run_bms_demo(args: argparse.Namespace) -> int:
    interval = args.interval
    duration = args.duration

    if args.port:
        transport = SerialTransport(args.port, baudrate=args.baudrate)
        transport.open()
        sim = None
        print(f"BMS demo on real port {args.port} @ {args.baudrate} baud (unit {args.unit})")
    else:
        app_end, dev_end = create_loopback_pair()
        sim = BmsSimulator(dev_end, unit_id=args.unit)
        sim.start()
        transport = app_end
        print(f"BMS demo on built-in simulator (unit {args.unit}) — no hardware required")

    client = BmsClient(transport, unit_id=args.unit, timeout=args.timeout)
    print("-" * 84)

    start = time.monotonic()
    next_poll = start
    comm_errors = 0
    triggered_overcurrent = False
    triggered_overtemp = False
    rc = 0
    try:
        while True:
            elapsed = time.monotonic() - start
            if elapsed >= duration:
                break

            # Scripted fault scenarios (only meaningful against the simulator).
            if sim is not None and not triggered_overcurrent and elapsed >= duration * 0.4:
                triggered_overcurrent = True
                print(">> scenario: heavy discharge load + a dropped response")
                sim.set_load_current(-160.0)
                sim.inject_comm_timeout(1)
            if sim is not None and not triggered_overtemp and elapsed >= duration * 0.7:
                triggered_overtemp = True
                print(">> scenario: forced over-temperature warning + a CRC error")
                sim.force_warning(BatteryFlag.OVER_TEMP)
                sim.inject_crc_error()

            try:
                tel = client.read_telemetry()
                print(_format_row(elapsed, tel))
            except TransportTimeout:
                comm_errors += 1
                print(f"t={elapsed:5.1f}s  [COMM] timeout — no response (retrying)")
            except ModbusError as exc:
                comm_errors += 1
                print(f"t={elapsed:5.1f}s  [COMM] protocol error: {exc} (retrying)")

            next_poll += interval
            time.sleep(max(0.0, next_poll - time.monotonic()))
    except KeyboardInterrupt:
        print("\ninterrupted")
        rc = 130
    finally:
        if sim is not None:
            sim.stop()
        transport.close()

    print("-" * 84)
    print(f"done — {comm_errors} comm error(s) detected and handled gracefully")
    return rc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fae-toolkit",
        description="FAE Toolkit — industrial device communication testing.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    demo = sub.add_parser("bms-demo", help="poll a BMS (simulator or real port)")
    demo.add_argument("--port", help="serial port (e.g. COM3 or /dev/ttyUSB0); omit to simulate")
    demo.add_argument("--baudrate", type=int, default=9600)
    demo.add_argument("--unit", type=int, default=1, help="Modbus unit id")
    demo.add_argument("--interval", type=float, default=0.5, help="poll interval seconds")
    demo.add_argument("--duration", type=float, default=10.0, help="run time seconds")
    demo.add_argument("--timeout", type=float, default=1.0, help="per-read timeout seconds")
    demo.set_defaults(func=run_bms_demo)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
