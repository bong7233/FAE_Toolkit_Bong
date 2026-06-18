# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.1.0] — unreleased

First public version. To publish, push a `v0.1.0` tag — CI builds and attaches
the Windows/Linux executables to the GitHub Release automatically.

### Added
- **Battery (BMS) module** — Modbus-RTU client/server (CRC-16/MODBUS) written
  from scratch, register map + engineering-unit decoding, a discharging device
  simulator with fault injection (comm timeout, CRC error, alarms), CLI
  (`bms-demo`) and a PySide6 GUI tab with live plots and CSV logging.
- **IO / PIO module** — Modbus coils/discrete-inputs/input-registers, a remote
  IO simulator that enforces a safety interlock (motion outputs refused while
  E-stop is tripped) and drives a light tower; CLI (`io-demo`) and GUI tab.
- **CAN BMS module** — periodic broadcast telemetry over python-can's virtual
  bus, client + simulator, CLI (`can-demo`) and GUI tab.
- **Teaching-point manager** — model/validation, JSON & CSV import/export, and
  a 2D map GUI (nodes by type, routes, validation).
- **C++ core** — CRC/Modbus in C++17 (CMake + CTest) plus a `fae_crc` utility,
  and a **pybind11** binding (`faecore`) verified to match Python byte-for-byte.
- **ROS 2 bridge** — `ament_python` package publishing battery/IO telemetry to
  ROS 2 topics (built with colcon in CI).
- **Simulator-backed everything** — runs with no hardware; the real pyserial
  path is covered in CI via a socat virtual serial pair, and
  `bms-sim-serve` exposes the simulator on a real port.
- **CI/CD** — GitHub Actions matrix (Windows + Linux): ruff + pytest, offscreen
  GUI smoke, C++ build/test, pybind11 parity, ROS 2 colcon build; on a version
  tag, standalone CLI + GUI executables are built, smoke-tested and released.

[0.1.0]: https://github.com/bong7233/FAE_Toolkit_Bong/releases/tag/v0.1.0
