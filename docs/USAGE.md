# 사용 가이드 (Usage)

> 🌐 **한국어** (기본) · [English](USAGE.en.md) · [⬅ README](../README.md)

이 문서는 **설치 없이 실행하는 법**과 **파이썬으로 실행하는 법**, 그리고 각 앱(Comm Tester / TeachingManager / CLI) 사용법을 다룹니다.
실제 하드웨어 연결은 **[HARDWARE](HARDWARE.md)**, 코드 수정·빌드는 **[DEVELOPMENT](DEVELOPMENT.md)** 를 참고하세요.

---

## 1. 가장 쉬운 방법 — 단독 실행파일 (파이썬 불필요)

1. **[Releases](https://github.com/bong7233/FAE_Toolkit_Bong/releases)** 페이지로 이동합니다.
2. 운영체제에 맞는 파일을 내려받습니다.

| 실행파일 | 설명 |
|---|---|
| `comm-tester-windows.exe` / `comm-tester-linux` | Comm Tester GUI |
| `teaching-manager-windows.exe` / `teaching-manager-linux` | TeachingManager GUI |
| `fae-toolkit-cli-windows.exe` / `fae-toolkit-cli-linux` | 헤드리스 CLI |

3. 실행합니다.
   - **Windows**: 더블클릭. (SmartScreen 경고가 뜨면 *추가 정보 → 실행*)
   - **Linux**:
     ```bash
     chmod +x comm-tester-linux
     ./comm-tester-linux
     ```

> 실행파일은 PyInstaller로 패키징되어 있어 별도 설치가 필요 없습니다. 첫 실행 시 압축 해제로 수 초가 걸릴 수 있습니다.

---

## 2. 파이썬으로 실행 (개발/평가용)

Python 3.10+ 필요.

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

## 3. Comm Tester 사용법

통신 유형별 탭(**Serial · TCP/IP · UDP · CAN**)으로 나뉘어 있고, 각 탭은 해당 통신의 파라미터만 보여줍니다.

### 기본 흐름
1. **탭 선택** → 통신 방식 선택 (예: Serial).
2. **연결 설정** 입력
   - Serial: 포트(목록에서 선택, *새로고침*), 통신 속도, 데이터/정지 비트, 패리티
   - TCP/IP: 모드(클라이언트/서버), 호스트, 포트
   - UDP: 원격 호스트/포트, 로컬 포트
   - CAN: 인터페이스, 채널, 비트레이트
3. **연결(Connect)** — 포트/소켓/버스가 없으면 **연결 실패**합니다(가짜 값 주입 없음).
4. **프레임 송신(Send frame)**
   - 형식 **HEX**(예: `01 03 00 00 00 0A`) 또는 **ASCII** 선택
   - 옵션: **Modbus CRC-16 자동첨부**, **CR+LF 추가**, **주기 반복(ms)**
   - **Send** 클릭 → 송신
5. **모니터(TX/RX)** — 송수신이 타임스탬프와 함께 표시됩니다.
   - 표시 옵션: **HEX / ASCII / 타임스탬프 / 자동 스크롤**
   - **Decode Modbus** 체크 시 각 프레임 아래에 해석이 붙습니다
     (송신=요청, 수신=응답 → 함수·레지스터/비트·예외·CRC). 예:
     `└─ unit 1  REQ Read Holding Registers  start=0 count=10  [CRC OK]`
   - **로그 저장…** 으로 텍스트 저장

### 저장 프레임 (매크로)
제조사마다 다른 프레임을 **이름·그룹(제조사)으로 저장**해 두고 한 번에 불러옵니다.
- **현재 저장…** : 지금 입력한 프레임/옵션을 이름과 그룹으로 저장
- 목록에서 더블클릭(또는 **불러오기**) → 송신창에 적용
- **삭제** : 선택 항목 제거
- 첫 실행 시 BMS / IO / ASCII 예시가 시드되어 있습니다.
- 저장 위치: `~/.fae_toolkit/macros_<탭>.json` (탭별로 분리 보관)

### 언어 전환
상단 메뉴 **언어(Language) → English / 한국어** 로 즉시 전환됩니다(재시작 불필요).

---

## 4. TeachingManager 사용법

AGV 티칭 포인트(좌표/이름/타입)를 표와 2D 맵으로 관리합니다.

- **샘플** : 예제 프로젝트 불러오기
- **포인트 추가 / 삭제** : 표에서 행 편집
- **검증(Validate)** : 좌표 중복·범위 등 점검 후 로그 표시
- **열기… / 저장…** : 프로젝트 JSON 입출력
- **CSV 내보내기…** : 표를 CSV로 저장

---

## 5. CLI (헤드리스 / 자동화)

GUI 없이 동작하는 데모·에뮬레이터 진입점입니다. 디스플레이가 없는 서버/CI에서도 동작합니다.

```bash
fae-toolkit bms-demo        --port /dev/ttyUSB0 --baudrate 9600 --unit 1   # BMS(Modbus) 폴링
fae-toolkit io-demo         --port /dev/ttyUSB0                            # 원격 IO/PIO
fae-toolkit can-demo                                                        # CAN(가상 버스)
fae-toolkit bms-sim-serve   --port /tmp/ttyA --baudrate 115200            # 가짜 BMS 슬레이브 서빙
fae-toolkit teaching-demo                                                   # 샘플 티칭 검증
```

각 명령의 옵션은 `fae-toolkit <명령> --help` 로 확인하세요.

---

## 6. 하드웨어 없이 시연하기

실제 장비가 없어도 **실제와 동일한 코드 경로**로 송수신을 시연할 수 있습니다.

- **TCP/UDP**: Comm Tester를 두 개 띄워 한쪽은 *서버(수신대기)*, 다른 쪽은 *클라이언트*로 연결.
- **Serial**: 가상 시리얼 페어 + 시뮬레이터(디바이스 역할).
  ```bash
  socat -d -d PTY,link=/tmp/ttyA,raw,echo=0 PTY,link=/tmp/ttyB,raw,echo=0
  fae-toolkit bms-sim-serve --port /tmp/ttyA --baudrate 115200   # 가짜 BMS 슬레이브
  fae-toolkit-gui   # Serial 탭에서 /tmp/ttyB 연결 → '01 03 00 00 00 0A' + CRC 송신
  ```
- **CAN**: `fae-toolkit can-demo` (python-can `virtual` 버스).

자세한 내용은 **[HARDWARE](HARDWARE.md)** 참고.
