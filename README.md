# FAE Toolkit

> 현장 엔지니어를 위한 **크로스플랫폼(Windows · Linux) 통신 테스트 도구 모음**.
> 통신 유형별(Serial · TCP · UDP · CAN)로 **파라미터와 송수신 프레임을 직접 설정**해 **실제 장비와 통신**하고,
> 별도 앱 **TeachingManager**로 AGV 티칭 포인트를 관리합니다. (Hercules / RealTerm / Docklight 스타일)

[![CI](https://github.com/bong7233/FAE_Toolkit_Bong/actions/workflows/ci.yml/badge.svg)](https://github.com/bong7233/FAE_Toolkit_Bong/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 미리보기

![Comm Tester live demo](docs/demo_comm.gif)

> **Comm Tester** — TCP 탭에서 실제 소켓에 연결하고, HEX/ASCII 프레임을 직접 입력해 송신하면
> 송수신이 타임스탬프와 함께 모니터에 표시됩니다. (가짜 값 없음 — 연결할 대상이 없으면 연결 실패)

| Serial 탭 | TCP 탭 (실제 송수신) | CAN 탭 | TeachingManager |
|---|---|---|---|
| ![serial](docs/screenshot_comm_serial.png) | ![tcp](docs/screenshot_comm_tcp.png) | ![can](docs/screenshot_comm_can.png) | ![teaching](docs/screenshot_teaching.png) |

## 설계 원칙

1. **실제 연결** — 포트/소켓/버스가 없으면 연결이 **실패**합니다. 자동으로 주입되는 가짜 텔레메트리가 없습니다.
2. **사용자 정의 프레임** — 제조사마다 다른 프레임을 **HEX/ASCII로 직접 입력**하고, Modbus CRC-16 자동첨부·CR+LF·주기 송신 옵션을 켤 수 있습니다.
3. **통신 유형 중심** — Serial / TCP / UDP / CAN 탭. 각 탭은 해당 통신의 파라미터만 노출합니다.
4. **하드웨어 없이도 정직하게** — 가상 시리얼 페어(socat/com0com), 로컬 에코(TCP/UDP), CAN virtual, 또는 동봉된 **디바이스 에뮬레이터**로 시연합니다(가짜 대시보드가 아니라 실제 송수신).
5. **KO/EN 토글** — 메뉴에서 언어 전환(혼합 표기 제거).

## 구성

| 모듈 | 내용 | 상태 |
|------|------|------|
| **Comm Tester** (앱) | Serial/TCP/UDP/CAN 탭, 프레임 직접입력, 실제연결, 송수신 모니터 | ✅ |
| **TeachingManager** (앱) | 별도 프로그램. 티칭 포인트/루트 2D 관리·검증·JSON/CSV | ✅ |
| 프로토콜 라이브러리 | Modbus-RTU / CRC-16 자체 구현 (탭의 프리셋 + 에뮬레이터에 재사용) | ✅ |
| 디바이스 에뮬레이터 | BMS/IO/CAN 시뮬레이터, `bms-sim-serve`(실제 포트에 가짜 슬레이브 서빙) | ✅ |
| C++ 코어 (+pybind11) | CRC/Modbus를 C++17로, Python과 바이트 동일성 검증 | ✅ |
| ROS 2 브릿지 | 텔레메트리를 ROS 2 토픽으로 (Linux, ament_python) | ✅ |

## 아키텍처

```
┌───────────────── 앱 1: Comm Tester (PySide6) ─────────────────┐
│  Serial │ TCP/IP │ UDP │ CAN   (탭별 파라미터 + 프레임 송신)   │
│   └─ 공통: 프레임 빌더(HEX/ASCII·CRC·주기) · 모니터(TX/RX)      │
├───────────────────────────────────────────────────────────────┤
│  Transport 계층 (공통 인터페이스)                              │
│   • SerialTransport(pyserial)  • Tcp/Udp Transport(socket)     │
│   • python-can (CAN)                                           │
└───────────────────────────────────────────────────────────────┘
┌─ 앱 2: TeachingManager ─┐   ┌─ 라이브러리/CLI ───────────────┐
│  포인트 표 + 2D 맵      │   │  Modbus/CRC, BMS/IO/CAN 에뮬레이터 │
└─────────────────────────┘   └────────────────────────────────┘
        +  C++ 코어(pybind11)  ·  ROS 2 브릿지  ·  GitHub Actions CI/CD
```

## 다운로드 (Releases)

설치 없이 쓰는 단독 실행파일은 **[Releases](https://github.com/bong7233/FAE_Toolkit_Bong/releases)** 에서.
`v*` 태그를 푸시하면 CI가 Comm Tester·TeachingManager 실행파일(Win/Linux)을 자동 빌드·첨부합니다.

## 빠른 시작

```bash
git clone https://github.com/bong7233/FAE_Toolkit_Bong.git
cd FAE_Toolkit_Bong
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[gui,dev]"

fae-toolkit-gui      # Comm Tester (Serial/TCP/UDP/CAN)
teaching-manager     # TeachingManager (별도 앱)
```

### 하드웨어 없이 시연하기 (정직한 방법)

```bash
# TCP/UDP: Comm Tester를 2개 띄워 한쪽 Server, 한쪽 Client로 연결 (또는 로컬 에코)
# Serial: 가상 시리얼 페어
socat -d -d PTY,link=/tmp/ttyA,raw,echo=0 PTY,link=/tmp/ttyB,raw,echo=0
fae-toolkit bms-sim-serve --port /tmp/ttyA --baudrate 115200   # 가짜 BMS 슬레이브를 실제 포트에 서빙
fae-toolkit-gui   # Serial 탭에서 /tmp/ttyB 연결 후 '01 03 00 00 00 0A' + CRC 송신
```

## 기술 스택

- **언어/런타임**: Python 3.10+ (PySide6), C++17/CMake + pybind11
- **통신**: pyserial(RS-232/485), socket(TCP/UDP), python-can(CAN), Modbus-RTU(자체구현)
- **품질/CI**: pytest, ruff, GitHub Actions (Windows+Linux 매트릭스 · C++ · pybind11 · ROS 2)

## 프로젝트 구조

```
src/fae_toolkit/
├── core/          transport(serial/tcp/udp), hexfmt, crc
├── protocols/     modbus, bms/io/can 프레임 정의 (프리셋·에뮬레이터용)
├── sim/           디바이스 에뮬레이터 (BMS/IO/CAN)
├── ui/            Comm Tester (comm/ 탭들, i18n, app)
├── teaching_manager/  TeachingManager (별도 앱)
└── cli.py         헤드리스 데모/에뮬레이터 진입점
cpp/               C++17 코어 (CRC/Modbus) + pybind11
ros2_bridge/       ROS 2 (ament_python) 브릿지
```

## 로드맵

- [x] 통신 유형별 Comm Tester (Serial/TCP/UDP/CAN) — 실제연결 + 프레임 직접입력 + 모니터
- [x] KO/EN 언어 토글
- [x] TeachingManager 별도 앱 분리
- [x] C++ 코어(+pybind11), ROS 2 브릿지, CI/CD
- [ ] 프리셋 확장 (Modbus 쓰기/디코드 뷰, 사용자 프레임 저장)
- [ ] 수신 프레임 프로토콜 디코더(Modbus 응답 파싱 표시)

## 저자

**이상봉 (Sangbong Lee)** — Robot S/W Engineer @ Zenix Robotics
- Portfolio: https://bongfae-production.up.railway.app/#about
- Email: batmantwo7233@gmail.com

## 라이선스

MIT — [LICENSE](LICENSE) 참조.
