# Usage

> 🌐 [한국어](USAGE.md) (default) · **English** · [⬅ README](../README.en.md)

This document covers **how to run without installation**, **how to run with Python**, and how to use each app (Comm Tester / TeachingManager / CLI).
For connecting real hardware, see **[HARDWARE](HARDWARE.en.md)**; for editing code and building, see **[DEVELOPMENT](DEVELOPMENT.en.md)**.

---

## 1. Easiest Method — Standalone Executable (no Python required)

1. Go to the **[Releases](https://github.com/bong7233/FAE_Toolkit_Bong/releases)** page.
2. Download the file for your operating system.

| Executable | Description |
|---|---|
| `comm-tester-windows.exe` / `comm-tester-linux` | Comm Tester GUI |
| `teaching-manager-windows.exe` / `teaching-manager-linux` | TeachingManager GUI |
| `fae-toolkit-cli-windows.exe` / `fae-toolkit-cli-linux` | Headless CLI |

3. Run it.
   - **Windows**: Double-click. (If a SmartScreen warning appears, choose *More info → Run*.)
   - **Linux**:
     ```bash
     chmod +x comm-tester-linux
     ./comm-tester-linux
     ```

> The executables are packaged with PyInstaller, so no separate installation is required. The first launch may take a few seconds for decompression.

---

## 2. Run with Python (for development/evaluation)

Python 3.10+ required.

```bash
git clone https://github.com/bong7233/FAE_Toolkit_Bong.git
cd FAE_Toolkit_Bong
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e ".[gui,dev]"

fae-toolkit-gui      # Comm Tester (Serial/TCP/UDP/CAN)
teaching-manager     # TeachingManager
fae-toolkit --help   # CLI
```

---

## 3. Using Comm Tester

It is divided into tabs by communication type (**Serial · TCP/IP · UDP · CAN**), and each tab shows only the parameters for that communication type.

### Basic Flow
1. **Select a tab** → choose the communication method (e.g., Serial).
2. Enter **connection settings**
   - Serial: port (select from the list, *refresh*), baud rate, data/stop bits, parity
   - TCP/IP: mode (client/server), host, port
   - UDP: remote host/port, local port
   - CAN: interface, channel, bitrate
3. **Connect** — If there is no port/socket/bus, the connection **fails** (no fake values injected).
4. **Send frame**
   - Choose the format **HEX** (e.g., `01 03 00 00 00 0A`) or **ASCII**
   - Options: **automatic Modbus CRC-16 appending**, **add CR+LF**, **periodic repeat (ms)**
   - Click **Send** → transmit
5. **Monitor (TX/RX)** — TX/RX is shown with timestamps.
   - Display options: **HEX / ASCII / timestamp / auto-scroll**
   - When **Decode Modbus** is checked, an interpretation is appended below each frame
     (TX=request, RX=response → function·register/bit·exception·CRC). Example:
     `└─ unit 1  REQ Read Holding Registers  start=0 count=10  [CRC OK]`
   - Save as text with **Save log…**

### Saved Frames (macros)
Save frames that differ per vendor **by name·group (vendor)** and load them all at once.
- **Save current…** : save the currently entered frame/options with a name and group
- Double-click an item in the list (or **Load**) → apply it to the send box
- **Delete** : remove the selected item
- BMS / IO / ASCII examples are seeded on first run.
- Storage location: `~/.fae_toolkit/macros_<tab>.json` (stored separately per tab)

### Switching Language
Switch instantly from the top menu **Language → English / 한국어** (no restart required).

---

## 4. Using TeachingManager

Manage AGV teaching points (coordinates/name/equipment type/status) with a table
and a **to-scale 2D map**.

**Basic actions**
- **Sample** : load the example project
- **Add / Delete point** : edit rows in the table (name·x·y·θ·station id)
- **Validate** : checks for duplicate coordinates, duplicate names, missing
  LOAD/UNLOAD, **alarm points**, etc., then shows a log
- **Open… / Save…** : project JSON I/O · **Export CSV…** : save the table as CSV

**Background drawing (CAD)** — the bottom *Background (CAD)* tab
- **Load image…** places a drawing / floor plan (PNG·JPG·BMP) under the map so
  you teach points on top of it.
- **Scale (mm/px)** matches it to real dimensions; the **Opacity** slider tunes
  readability. (Export your CAD to PNG/JPG; direct vector DXF loading is on the
  roadmap.)

**Custom equipment types** — the bottom *Equipment types* tab
- Assign a **color** and **marker shape** (circle/square/triangle/diamond/star/
  +/✕) per equipment type, freely.
- **Add type** creates a new equipment type; apply it to a point from the *type*
  column. On the map, **shape = equipment type**, **outline = type color**.

**Teaching status** — the *status* column (and the top dashboard)
- Store **In progress (amber) / Done (green) / Alarm (red)** per point.
  *Alarm* = taught but not working correctly and needing rework.
- The marker **fill = status**; the top chips summarize the counts per status.

---

## 5. CLI (Headless / Automation)

These are the demo/emulator entry points that run without a GUI. They work even on servers/CI without a display.

```bash
fae-toolkit bms-demo        --port /dev/ttyUSB0 --baudrate 9600 --unit 1   # poll a BMS (Modbus)
fae-toolkit io-demo         --port /dev/ttyUSB0                            # remote IO/PIO
fae-toolkit can-demo                                                        # CAN (virtual bus)
fae-toolkit bms-sim-serve   --port /tmp/ttyA --baudrate 115200            # serve a fake BMS slave
fae-toolkit teaching-demo                                                   # validate a sample teaching project
```

Check the options for each command with `fae-toolkit <command> --help`.

---

## 6. Demoing Without Hardware

Even without real equipment, you can demo TX/RX over the **exact same code path as the real thing**.

- **TCP/UDP**: Launch two instances of Comm Tester and connect one as the *server (listening)* and the other as the *client*.
- **Serial**: virtual serial pair + simulator (acting as the device).
  ```bash
  socat -d -d PTY,link=/tmp/ttyA,raw,echo=0 PTY,link=/tmp/ttyB,raw,echo=0
  fae-toolkit bms-sim-serve --port /tmp/ttyA --baudrate 115200   # fake BMS slave
  fae-toolkit-gui   # in the Serial tab connect /tmp/ttyB → send '01 03 00 00 00 0A' + CRC
  ```
- **CAN**: `fae-toolkit can-demo` (python-can `virtual` bus).

For details, see **[HARDWARE](HARDWARE.en.md)**.
