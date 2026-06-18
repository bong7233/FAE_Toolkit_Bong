# 개발 가이드 (Development)

> 🌐 **한국어** (기본) · [English](DEVELOPMENT.en.md) · [⬅ README](../README.md)

**코드를 가져와서 → 실행/수정 → 테스트 → 다시 빌드(컴파일) → 배포(릴리스)** 하는 전체 흐름을 정리합니다.

---

## 1. 개발 환경 준비

Python 3.10+ 필요. (실행파일 빌드는 OS별로 해당 OS에서 수행)

```bash
git clone https://github.com/bong7233/FAE_Toolkit_Bong.git
cd FAE_Toolkit_Bong
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# editable 설치 — 소스를 고치면 재설치 없이 바로 반영됨
pip install -e ".[gui,dev]"
```

- `gui` : PySide6/pyqtgraph/python-can (GUI 실행에 필요)
- `dev` : pytest, ruff (테스트/린트)
- `build` : pyinstaller (단독 실행파일 빌드)

> **IDE로 가져오기**: 위 폴더를 VS Code / PyCharm 등에서 열고, 인터프리터를 `.venv` 로 지정하면 됩니다. 고치고 `git push` 하면 CI가 자동으로 검증/빌드합니다(아래 6·7장).

---

## 2. 프로젝트 구조 — 무엇을 어디서 고치나

```
src/fae_toolkit/
├── core/              transport(serial/tcp/udp/can), hexfmt, crc, macros
├── protocols/         modbus(디코더 포함), bms/io/can 프레임 정의
├── sim/               디바이스 에뮬레이터 (BMS/IO/CAN)
├── ui/                Comm Tester
│   ├── comm/          탭(bytestream/can), 패널, 송신/모니터/매크로 위젯
│   ├── i18n.py        한/영 문자열 (키-값)
│   └── app.py, main_window.py
├── teaching_manager/  TeachingManager (별도 앱)
└── cli.py             헤드리스 CLI 진입점
cpp/                   C++17 코어 (CRC/Modbus) + pybind11
ros2_bridge/           ROS 2 (ament_python) 브릿지
packaging/             PyInstaller 진입점 (cli/gui/teaching)
tests/                 pytest
.github/workflows/ci.yml   CI/CD 정의
```

| 하고 싶은 일 | 고칠 곳 |
|---|---|
| 새 통신 탭 / 파라미터 추가 | `ui/comm/panels.py`, `ui/comm/*_tab.py` |
| 송신 옵션·프리셋 | `ui/comm/sender.py` |
| 모니터 표시·디코더 | `ui/comm/monitor.py`, `protocols/modbus.py` |
| 저장 프레임(매크로) | `core/macros.py`, `ui/comm/macros_panel.py` |
| 한/영 문구 | `ui/i18n.py` (`_STRINGS` 딕셔너리) |
| CLI 명령 | `cli.py` |

---

## 3. 실행하며 수정하기

```bash
fae-toolkit-gui          # Comm Tester 실행 후, 소스 고치고 다시 실행
teaching-manager
fae-toolkit bms-demo --help
```

GUI는 `QT_QPA_PLATFORM=offscreen` 환경변수로 **화면 없이도** 띄울 수 있어, 서버/원격에서 동작 확인이 가능합니다.

---

## 4. 테스트 & 린트 (커밋 전 필수)

```bash
# 전체 테스트 (GUI 스모크 포함 → 오프스크린)
QT_QPA_PLATFORM=offscreen pytest -q

# 린트 / 포맷 (CI와 동일 기준)
ruff check .
ruff format --check .
```

CI가 동일한 명령을 Windows·Linux 양쪽에서 돌립니다. 로컬에서 통과하면 CI도 대개 통과합니다.

---

## 5. 다시 빌드(컴파일)

### 5-1. 단독 실행파일 (PyInstaller) — 가장 흔한 "다시 컴파일"

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

결과물은 `dist/` 에 생성됩니다. 동작 확인:
```bash
./dist/fae-toolkit --version
QT_QPA_PLATFORM=offscreen ./dist/comm-tester --self-test
QT_QPA_PLATFORM=offscreen ./dist/teaching-manager --self-test
```

> 실행파일은 **빌드한 OS 전용**입니다. Windows용 `.exe`는 Windows에서, Linux용은 Linux에서 빌드해야 합니다. (그래서 CI가 양쪽 OS에서 빌드합니다.)

### 5-2. C++ 코어 (CMake / CTest)

```bash
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build --config Release
ctest --test-dir cpp/build -C Release --output-on-failure
```

### 5-3. pybind11 모듈 (C++ ↔ Python)

```bash
pip install pybind11
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release -DFAE_BUILD_PYBIND=ON \
    -Dpybind11_DIR="$(python -m pybind11 --cmakedir)"
cmake --build cpp/build --config Release
PYTHONPATH=cpp/build/py python cpp/python/check_bindings.py   # Python과 바이트 동일성 검증
```

---

## 6. CI/CD — push 하면 자동으로 일어나는 일

`.github/workflows/ci.yml` 에 정의되어 있고, **푸시/PR 마다** GitHub의 클라우드 러너에서 실행됩니다.

| Job | 내용 | OS |
|---|---|---|
| Lint & test | ruff + pytest | Windows, Linux |
| GUI smoke | 오프스크린으로 GUI 구동 | Linux |
| C++ build & test | CMake + CTest | Windows, Linux |
| pybind11 | C++↔Python 동일성 | Windows, Linux |
| ROS 2 bridge | colcon 빌드 + import | Linux (humble) |
| **package** | 단독 실행파일 빌드·첨부 | Windows, Linux **(태그일 때만)** |

즉, **그냥 push** 하면 검증(테스트/빌드)까지 자동으로 되고, **버전 태그(`v*`)를 push** 하면 거기에 더해 실행파일을 빌드해 릴리스에 첨부합니다.

---

## 7. 릴리스 끊기 (실행파일 자동 배포)

1. **버전 올리기** (세 곳을 같은 값으로):
   - `src/fae_toolkit/__init__.py` → `__version__`
   - `pyproject.toml` → `version`
   - `ros2_bridge/package.xml`, `ros2_bridge/setup.py` → `version`
2. `CHANGELOG.md` 에 변경점 추가, 커밋·푸시(`main` 녹색 확인).
3. **태그 생성** — 둘 중 하나:

   **A. GitHub 웹 (추천, 터미널 불필요)**
   - *Releases → Draft a new release → Choose a tag* 에 `vX.Y.Z` 입력 → *Create new tag on publish*
   - Target: `main` → *Publish release*

   **B. 로컬 git**
   ```bash
   git tag -a vX.Y.Z -m "FAE Toolkit vX.Y.Z"
   git push origin vX.Y.Z
   ```

→ 태그가 원격에 생기면 CI `package` job이 돌아 **Win/Linux 실행파일 6종(앱 3 × OS 2)** 을 빌드해 해당 릴리스에 자동 첨부합니다(약 10~20분).

> 일부 관리형/클라우드 환경에서는 보안상 **태그 push가 막힐 수** 있습니다(HTTP 403). 그럴 땐 위 **A(웹 UI)** 또는 본인 PC에서 **B** 로 태그를 만들면 됩니다.

---

## 8. 기여 흐름 요약

```
브랜치 생성 → 코드 수정 → (4) 테스트·린트 통과 → 커밋·푸시
   → CI 녹색 확인 → main 반영 → 필요 시 (7) 태그로 릴리스
```
