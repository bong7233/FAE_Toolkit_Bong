# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- **TeachingManager upgrade** — a far richer editor:
  - **CAD/floor-plan background**: load a drawing (PNG/JPG/BMP), set its scale
    (mm/px) and opacity, and teach points on top of it.
  - **Teaching status** per point — *in progress / done / alarm* — saved in the
    project, shown as the marker fill colour and summarised in a dashboard.
  - **Customisable equipment types**: pick a colour and marker shape per type,
    and add your own types (marker shape = type, outline = type colour).
  - Modernised look (styled toolbar, status chips, tabbed Background/Types/Log).
- Bilingual documentation (Korean default + English `*.en.md`): USAGE,
  DEVELOPMENT, PORTFOLIO, HARDWARE; README architecture as a Mermaid diagram.

### Changed
- Teaching model: `TeachingPoint.type` is now free-form text (custom equipment
  types) with `status`; projects carry an `EquipmentStyle` table and optional
  background image. Older JSON files still load.

### Fixed
- CI: a flaky offscreen-GUI stall could hang until the job timeout and *cancel*
  the run. Added `pytest-timeout` (per-test 120s) so hangs fail fast, and
  tightened the GUI-smoke job timeout.

## [0.2.0] — 2026-06-18

Field-usability redesign. Push a `v0.2.0` tag and CI builds/attaches the
Windows/Linux executables to the GitHub Release automatically.

### Changed
- **Redesigned into the Comm Tester** — replaced the simulator-dashboard GUI
  with a transport-centric tester built around **Serial / TCP / UDP / CAN**
  tabs. Real connections (open fails if the device/host is unavailable),
  user-defined TX frames (HEX/ASCII, optional Modbus CRC-16 / CR+LF / periodic
  send), and a timestamped TX/RX monitor (HEX + ASCII). No auto-injected fake
  telemetry.
- **TeachingManager split out** into its own app (`teaching-manager`).
- **KO/EN language toggle** replaces the mixed-language labels.

### Added
- **Modbus frame decoder** — optional "Decode Modbus" view in the monitor
  annotates each frame (TX as request, RX as response) with the function,
  registers/bits/exception, and CRC status.
- **Saved frames (macros)** — store frequently used frames per maker and recall
  them with one click; persisted to JSON, kept separately per transport tab,
  and seeded with a field-realistic starter library (BMS / IO / ASCII).

## [0.1.0] — 2026-06-18

Initial public release (pre-redesign): battery (BMS) / IO / CAN telemetry GUI
with bundled device simulators, the Modbus-RTU + CRC-16 protocol library, the
C++ core (pybind11), the ROS 2 bridge, and the GitHub Actions CI/CD matrix that
builds & attaches standalone Windows/Linux executables.

[0.2.0]: https://github.com/bong7233/FAE_Toolkit_Bong/releases/tag/v0.2.0
[0.1.0]: https://github.com/bong7233/FAE_Toolkit_Bong/releases/tag/v0.1.0
