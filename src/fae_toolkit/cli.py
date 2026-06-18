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
from fae_toolkit.protocols.io import IoClient, io_map
from fae_toolkit.protocols.modbus import ModbusError, ModbusException
from fae_toolkit.sim.bms import BmsSimulator
from fae_toolkit.sim.io import IoSimulator
from fae_toolkit.teaching import export_points_csv, sample_project, save_project, validate


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


def _io_status_row(elapsed: float, snap) -> str:
    lock = "OK  " if snap.interlock_ok else "OPEN"
    di = ",".join(snap.active_inputs()) or "-"
    do = ",".join(snap.active_outputs()) or "-"
    return (
        f"t={elapsed:5.1f}s  interlock={lock}  "
        f"dist={snap.ai[io_map.AI_DISTANCE]:6.1f}mm  "
        f"w={snap.ai[io_map.AI_WEIGHT]:4.1f}kg  "
        f"DI[{di}]  DO[{do}]"
    )


def run_io_demo(args: argparse.Namespace) -> int:
    if args.port:
        transport = SerialTransport(args.port, baudrate=args.baudrate)
        transport.open()
        sim = None
        print(f"IO demo on real port {args.port} @ {args.baudrate} baud (unit {args.unit})")
    else:
        app_end, dev_end = create_loopback_pair()
        sim = IoSimulator(dev_end, unit_id=args.unit)
        sim.start()
        transport = app_end
        print(f"IO demo on built-in simulator (unit {args.unit}) — no hardware required")

    client = IoClient(transport, unit_id=args.unit, timeout=args.timeout)
    print("-" * 96)

    start = time.monotonic()
    next_poll = start
    done_steps = set()
    rc = 0
    try:
        while True:
            elapsed = time.monotonic() - start
            if elapsed >= args.duration:
                break

            if sim is not None and "load" not in done_steps and elapsed >= args.duration * 0.25:
                done_steps.add("load")
                print(">> scenario: load handshake — clamp + lift up")
                client.set_output(io_map.DO_LOAD_CLAMP, True)
                client.set_output(io_map.DO_LIFT_UP, True)
            if sim is not None and "estop" not in done_steps and elapsed >= args.duration * 0.5:
                done_steps.add("estop")
                print(">> scenario: E-STOP tripped — try to run conveyor (should be refused)")
                sim.trip_estop(True)
                try:
                    client.set_output(io_map.DO_CONVEYOR, True)
                    print("   conveyor turned ON (unexpected!)")
                except ModbusException as exc:
                    print(f"   interlock refused conveyor → {type(exc).__name__}")
            if sim is not None and "clear" not in done_steps and elapsed >= args.duration * 0.75:
                done_steps.add("clear")
                print(">> scenario: clear E-STOP and retry conveyor")
                sim.clear_faults()
                client.set_output(io_map.DO_CONVEYOR, True)

            try:
                print(_io_status_row(elapsed, client.read_snapshot()))
            except TransportTimeout:
                print(f"t={elapsed:5.1f}s  [COMM] timeout — no response")
            except ModbusError as exc:
                print(f"t={elapsed:5.1f}s  [COMM] protocol error: {exc}")

            next_poll += args.interval
            time.sleep(max(0.0, next_poll - time.monotonic()))
    except KeyboardInterrupt:
        print("\ninterrupted")
        rc = 130
    finally:
        if sim is not None:
            sim.stop()
        transport.close()

    print("-" * 96)
    print("done")
    return rc


def run_teaching_demo(args: argparse.Namespace) -> int:
    project = sample_project()
    print(f"Teaching project '{project.name}' (v{project.version})")
    print(f"  points: {len(project.points)}")
    for p in project.points:
        print(
            f"    [{p.id}] {p.name:13s} {p.type.value:8s} "
            f"({p.x:6.0f},{p.y:6.0f}) θ={p.theta:4.0f}  {p.station}"
        )
    print(f"  routes: {len(project.routes)}")
    for route in project.routes:
        names = " -> ".join(
            project.get_point(i).name for i in route.point_ids if project.get_point(i)
        )
        print(f"    {route.name}: {names}")

    issues = validate(project)
    print(f"  validation: {len(issues)} issue(s)")
    for issue in issues:
        print(f"    - {issue}")

    if args.out:
        save_project(project, args.out)
        csv_path = args.out.rsplit(".", 1)[0] + ".csv"
        export_points_csv(project, csv_path)
        print(f"saved {args.out} and {csv_path}")
    return 0


def run_can_demo(args: argparse.Namespace) -> int:
    import can  # optional dependency, imported lazily

    from fae_toolkit.protocols.canbus import CanBmsClient
    from fae_toolkit.sim.can_bms import CanBmsSimulator

    sim = None
    if args.interface == "virtual":
        dev_bus = can.Bus(interface="virtual", channel=args.channel, receive_own_messages=False)
        app_bus = can.Bus(interface="virtual", channel=args.channel, receive_own_messages=False)
        sim = CanBmsSimulator(dev_bus)
        sim.start()
        print(f"CAN BMS demo on virtual bus '{args.channel}' — no hardware required")
    else:
        dev_bus = None
        app_bus = can.Bus(interface=args.interface, channel=args.channel)
        print(f"CAN BMS demo on {args.interface}:{args.channel}")

    client = CanBmsClient(app_bus, timeout=args.timeout)
    print("-" * 72)
    start = time.monotonic()
    next_poll = start
    triggered = False
    rc = 0
    try:
        while True:
            elapsed = time.monotonic() - start
            if elapsed >= args.duration:
                break
            if sim is not None and not triggered and elapsed >= args.duration * 0.5:
                triggered = True
                print(">> scenario: heavy discharge + forced over-temperature")
                sim.set_load_current(-160.0)
                sim.force_warning(BatteryFlag.OVER_TEMP)
            try:
                st = client.read_state()
                status = "OK" if not st.has_alarm else "ALARM: " + ", ".join(st.active_flags())
                print(
                    f"t={elapsed:5.1f}s  V={st.voltage:6.2f}  I={st.current:+7.2f}A  "
                    f"SOC={st.soc:5.1f}%  T={st.max_temp:4.1f}C  [{status}]"
                )
            except TransportTimeout:
                print(f"t={elapsed:5.1f}s  [CAN] no telemetry (timeout)")
            next_poll += args.interval
            time.sleep(max(0.0, next_poll - time.monotonic()))
    except KeyboardInterrupt:
        rc = 130
    finally:
        if sim is not None:
            sim.stop()
        app_bus.shutdown()
        if dev_bus is not None:
            dev_bus.shutdown()
    print("-" * 72)
    print("done")
    return rc


def run_bms_sim_serve(args: argparse.Namespace) -> int:
    """Bind the BMS simulator to a real serial port so it acts as a device.

    Point this at one end of a virtual serial pair (socat/com0com) or a real
    RS-232/485 adapter, then connect any Modbus master (including
    ``fae-toolkit bms-demo --port <other-end>``).
    """
    transport = SerialTransport(args.port, baudrate=args.baudrate)
    transport.open()
    sim = BmsSimulator(transport, unit_id=args.unit)
    sim.start()
    print(f"BMS simulator serving on {args.port} @ {args.baudrate} baud (unit {args.unit})")
    print("Ctrl+C to stop" if args.duration <= 0 else f"running for {args.duration}s")
    rc = 0
    try:
        if args.duration > 0:
            time.sleep(args.duration)
        else:
            while True:
                time.sleep(0.5)
    except KeyboardInterrupt:
        rc = 130
    finally:
        sim.stop()
        transport.close()
    return rc


def _add_link_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--port", help="serial port (e.g. COM3 or /dev/ttyUSB0); omit to simulate")
    parser.add_argument("--baudrate", type=int, default=9600)
    parser.add_argument("--unit", type=int, default=1, help="Modbus unit id")
    parser.add_argument("--interval", type=float, default=0.5, help="poll interval seconds")
    parser.add_argument("--duration", type=float, default=10.0, help="run time seconds")
    parser.add_argument("--timeout", type=float, default=1.0, help="per-read timeout seconds")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fae-toolkit",
        description="FAE Toolkit — industrial device communication testing.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    bms = sub.add_parser("bms-demo", help="poll a BMS (simulator or real port)")
    _add_link_args(bms)
    bms.set_defaults(func=run_bms_demo)

    io = sub.add_parser("io-demo", help="exercise a remote-IO/PIO block (simulator or real port)")
    _add_link_args(io)
    io.set_defaults(func=run_io_demo)

    teaching = sub.add_parser("teaching-demo", help="build and validate a sample teaching project")
    teaching.add_argument("--out", help="write the project to this .json (and a .csv next to it)")
    teaching.set_defaults(func=run_teaching_demo)

    serve = sub.add_parser("bms-sim-serve", help="run the BMS simulator on a real serial port")
    serve.add_argument("--port", required=True, help="serial port (e.g. /dev/pts/3, COM4)")
    serve.add_argument("--baudrate", type=int, default=9600)
    serve.add_argument("--unit", type=int, default=1, help="Modbus unit id")
    serve.add_argument("--duration", type=float, default=0.0, help="run seconds (0 = until Ctrl+C)")
    serve.set_defaults(func=run_bms_sim_serve)

    can_demo = sub.add_parser("can-demo", help="read a CAN BMS (virtual bus or real interface)")
    can_demo.add_argument("--interface", default="virtual", help="python-can interface")
    can_demo.add_argument("--channel", default="fae_demo", help="CAN channel name")
    can_demo.add_argument("--interval", type=float, default=0.5, help="poll interval seconds")
    can_demo.add_argument("--duration", type=float, default=10.0, help="run time seconds")
    can_demo.add_argument("--timeout", type=float, default=1.0, help="per-read timeout seconds")
    can_demo.set_defaults(func=run_can_demo)
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
