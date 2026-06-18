# Development

> 🌐 [한국어](DEVELOPMENT.md) (default) · **English** · [⬅ README](../README.en.md)

This document summarizes the entire flow of **getting the code → running/editing → testing → rebuilding (compiling) → deploying (releasing)**.

---

## 1. Setting Up the Development Environment

Python 3.10+ required. (Executable builds are done per OS on the matching OS.)

```bash
git clone https://github.com/bong7233/FAE_Toolkit_Bong.git
cd FAE_Toolkit_Bong
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# editable install — edits to the source take effect immediately, no reinstall needed
pip install -e ".[gui,dev]"
```

- `gui` : PySide6/pyqtgraph/python-can (required to run the GUI)
- `dev` : pytest, ruff (testing/linting)
- `build` : pyinstaller (standalone executable build)

> **Importing into an IDE**: Open the folder above in VS Code / PyCharm, etc., and set the interpreter to `.venv`. Once you edit and `git push`, CI automatically validates/builds (sections 6·7 below).

---

## 2. Project Structure — What to Edit and Where

```
src/fae_toolkit/
├── core/              transport(serial/tcp/udp/can), hexfmt, crc, macros
├── protocols/         modbus (incl. decoder), bms/io/can frame definitions
├── sim/               device emulators (BMS/IO/CAN)
├── ui/                Comm Tester
│   ├── comm/          tabs(bytestream/can), panels, send/monitor/macro widgets
│   ├── i18n.py        KO/EN strings (key-value)
│   └── app.py, main_window.py
├── teaching_manager/  TeachingManager (separate app)
└── cli.py             headless CLI entry point
cpp/                   C++17 core (CRC/Modbus) + pybind11
ros2_bridge/           ROS 2 (ament_python) bridge
packaging/             PyInstaller entry points (cli/gui/teaching)
tests/                 pytest
.github/workflows/ci.yml   CI/CD definition
```

| What you want to do | Where to edit |
|---|---|
| Add a new communication tab / parameter | `ui/comm/panels.py`, `ui/comm/*_tab.py` |
| Send options·presets | `ui/comm/sender.py` |
| Monitor display·decoder | `ui/comm/monitor.py`, `protocols/modbus.py` |
| Saved frames (macros) | `core/macros.py`, `ui/comm/macros_panel.py` |
| KO/EN strings | `ui/i18n.py` (`_STRINGS` dictionary) |
| CLI commands | `cli.py` |

---

## 3. Editing While Running

```bash
fae-toolkit-gui          # run Comm Tester, then edit the source and run again
teaching-manager
fae-toolkit bms-demo --help
```

The GUI can be launched **even without a screen** via the `QT_QPA_PLATFORM=offscreen` environment variable, so you can verify behavior on a server/remotely.

---

## 4. Tests & Lint (required before committing)

```bash
# full test suite (incl. GUI smoke → offscreen)
QT_QPA_PLATFORM=offscreen pytest -q

# lint / format (same criteria as CI)
ruff check .
ruff format --check .
```

CI runs the same commands on both Windows·Linux. If it passes locally, CI usually passes too.

---

## 5. Rebuilding (compiling)

### 5-1. Standalone Executable (PyInstaller) — the most common "recompile"

```bash
pip install -e ".[gui,build]"

# CLI
pyinstaller --noconfirm --onefile --name fae-toolkit --paths src packaging/cli_entry.py
# Comm Tester GUI
pyinstaller --noconfirm --onefile --name comm-tester --paths src \
    --hidden-import can.interfaces.virtual packaging/gui_entry.py
# TeachingManager GUI
pyinstaller --noconfirm --onefile --name teaching-manager --paths src packaging/teaching_entry.py
```

The output is generated in `dist/`. Verify operation:
```bash
./dist/fae-toolkit --version
QT_QPA_PLATFORM=offscreen ./dist/comm-tester --self-test
QT_QPA_PLATFORM=offscreen ./dist/teaching-manager --self-test
```

> Executables are **only for the OS they were built on**. A Windows `.exe` must be built on Windows, and a Linux one on Linux. (That is why CI builds on both OSes.)

### 5-2. C++ Core (CMake / CTest)

```bash
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build --config Release
ctest --test-dir cpp/build -C Release --output-on-failure
```

### 5-3. pybind11 Module (C++ ↔ Python)

```bash
pip install pybind11
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release -DFAE_BUILD_PYBIND=ON \
    -Dpybind11_DIR="$(python -m pybind11 --cmakedir)"
cmake --build cpp/build --config Release
PYTHONPATH=cpp/build/py python cpp/python/check_bindings.py   # verify byte-identity with Python
```

---

## 6. CI/CD — What Happens Automatically on Push

It is defined in `.github/workflows/ci.yml` and runs on GitHub's cloud runners **on every push/PR**.

| Job | Contents | OS |
|---|---|---|
| Lint & test | ruff + pytest | Windows, Linux |
| GUI smoke | run the GUI offscreen | Linux |
| C++ build & test | CMake + CTest | Windows, Linux |
| pybind11 | C++↔Python parity | Windows, Linux |
| ROS 2 bridge | colcon build + import | Linux (humble) |
| **package** | build·attach standalone executables | Windows, Linux **(only on a tag)** |

In other words, **just pushing** automatically runs validation (tests/builds), and **pushing a version tag (`v*`)** additionally builds the executables and attaches them to the release.

---

## 7. Cutting a Release (automatic executable deployment)

1. **Bump the version** (the same value in three places):
   - `src/fae_toolkit/__init__.py` → `__version__`
   - `pyproject.toml` → `version`
   - `ros2_bridge/package.xml`, `ros2_bridge/setup.py` → `version`
2. Add the changes to `CHANGELOG.md`, then commit·push (confirm `main` is green).
3. **Create a tag** — one of the two:

   **A. GitHub web (recommended, no terminal needed)**
   - In *Releases → Draft a new release → Choose a tag*, enter `vX.Y.Z` → *Create new tag on publish*
   - Target: `main` → *Publish release*

   **B. Local git**
   ```bash
   git tag -a vX.Y.Z -m "FAE Toolkit vX.Y.Z"
   git push origin vX.Y.Z
   ```

→ Once the tag appears on the remote, the CI `package` job runs and builds **6 Win/Linux executables (3 apps × 2 OSes)**, automatically attaching them to that release (about 10–20 minutes).

> In some managed/cloud environments, **tag pushes may be blocked** for security reasons (HTTP 403). In that case, create the tag using **A (web UI)** above or **B** on your own PC.

---

## 8. Contribution Flow Summary

```
create a branch → edit code → (4) pass tests·lint → commit·push
   → confirm CI is green → merge to main → if needed, (7) release via a tag
```
