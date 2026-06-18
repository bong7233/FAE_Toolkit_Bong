# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.1.0] — unreleased

First public version. Push a `v0.1.0` tag and CI builds/attaches the
Windows/Linux executables to the GitHub Release automatically.

### Added
- **Comm Tester** (desktop app) — transport-centric communication tester with
  **Serial / TCP / UDP / CAN** tabs. Real connections (open fails if the
  device/host is unavailable), user-defined TX frames (HEX/ASCII, optional
  Modbus CRC-16 / CR+LF / periodic send), and a timestamped TX/RX monitor
  (HEX + ASCII). KO/EN language toggle.
- **Modbus frame decoder** — optional "Decode Modbus" view in the monitor
  annotates each frame (TX as request, RX as response) with the function,
  registers/bits/exception, and CRC status.
- **Saved frames (macros)** — store frequently used frames per maker and recall
  them with one click; persisted to JSON and kept separately per transport tab.
- **TeachingManager** (separate app) — AGV teaching-point manager: editable
  point table, live 2D map, validation, JSON/CSV import/export.
- **Transports** — `SerialTransport` (pyserial), `TcpClient/TcpServer/Udp`
  transports (sockets), CAN via python-can, behind one `Transport` interface.
- **Protocol library** — Modbus-RTU + CRC-16 implemented from scratch, reused as
  tester presets and by the device emulators.
- **Device emulators** — BMS/IO/CAN simulators and `bms-sim-serve` (serve a fake
  Modbus slave on a real/virtual serial port) for honest hardware-free testing.
- **C++ core** — CRC/Modbus in C++17 (CMake + CTest) with a pybind11 binding
  (`faecore`) verified byte-identical to Python.
- **ROS 2 bridge** — ament_python package publishing telemetry to ROS 2 topics.
- **CI/CD** — GitHub Actions matrix (Windows + Linux): ruff + pytest, offscreen
  GUI smoke, C++ build/test, pybind11 parity, ROS 2 colcon build; tagged
  releases build & attach standalone executables for both apps.

[0.1.0]: https://github.com/bong7233/FAE_Toolkit_Bong/releases/tag/v0.1.0
