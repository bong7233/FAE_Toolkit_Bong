# 실제 하드웨어 연동 가이드 (Hardware guide)

이 툴킷은 **실제 시리얼 포트(pyserial)** 와 **실제 CAN 인터페이스(python-can)** 에 그대로 연결됩니다.
시뮬레이터 + loopback은 하드웨어 없이 개발/평가하기 위한 것이고, 아래 방법으로 실제 포트 경로를
검증할 수 있습니다. (`bms-sim-serve` ↔ `bms-demo` 조합은 CI의 `test_serial_socat`이 검증하는 흐름과 동일합니다.)

---

## 1. 실제 시리얼 포트 (RS-232 / RS-485)

### Linux
```bash
# 포트 확인
dmesg | grep tty            # 보통 /dev/ttyUSB0, /dev/ttyACM0
sudo usermod -aG dialout $USER   # 권한 (재로그인 필요)

# BMS(Modbus) 폴링
fae-toolkit bms-demo --port /dev/ttyUSB0 --baudrate 9600 --unit 1
```

### Windows
```powershell
# 장치 관리자 → 포트(COM & LPT) 에서 COM 번호 확인
fae-toolkit bms-demo --port COM3 --baudrate 9600 --unit 1
```

## 2. 하드웨어 없이 "실제 포트 경로" 테스트 (가상 시리얼 페어)

가상 시리얼 페어를 만들고, 한쪽에 **시뮬레이터를 디바이스로** 띄운 뒤 다른 쪽에서 앱으로 연결하면
실제 RS-232/485와 **동일한 pyserial 코드 경로**로 동작합니다.

### Linux (socat)
```bash
socat -d -d PTY,link=/tmp/ttyA,raw,echo=0 PTY,link=/tmp/ttyB,raw,echo=0
# 터미널 1 — 시뮬레이터를 /tmp/ttyA 에 디바이스로 서빙
fae-toolkit bms-sim-serve --port /tmp/ttyA --baudrate 115200
# 터미널 2 — 앱을 /tmp/ttyB 에 연결
fae-toolkit bms-demo --port /tmp/ttyB --baudrate 115200
```

### Windows (com0com)
1. [com0com] 설치 후 `COM4 <-> COM5` 가상 페어 생성
2. `fae-toolkit bms-sim-serve --port COM4 --baudrate 115200`
3. `fae-toolkit bms-demo --port COM5 --baudrate 115200`

> `bms-sim-serve`는 포트에 **Modbus-RTU 슬레이브(가짜 BMS)** 를 띄웁니다. 우리 앱뿐 아니라
> 임의의 Modbus 마스터 툴(예: modpoll)로도 폴링할 수 있어, 다른 소프트웨어 디버깅용 더미로도 유용합니다.

## 3. CAN

### 가상 (하드웨어 불필요)
```bash
fae-toolkit can-demo            # python-can 'virtual' 버스
```

### 실제 CAN (Linux, SocketCAN)
```bash
sudo ip link set can0 type can bitrate 500000
sudo ip link set up can0
fae-toolkit can-demo --interface socketcan --channel can0
```

### 실제 CAN (Windows)
PCAN / Kvaser 등은 python-can 인터페이스로 지정합니다.
```powershell
fae-toolkit can-demo --interface pcan --channel PCAN_USBBUS1
```

## 4. 문제 해결 (Troubleshooting)

| 증상 | 점검 |
|------|------|
| 응답 없음(timeout) | baudrate / unit id / 배선(A-B, TX-RX) / 종단저항(RS-485) |
| CRC 에러 | 노이즈, 잘못된 baudrate, 접지 |
| 권한 오류(Linux) | `dialout` 그룹, 포트 점유 여부(`lsof <port>`) |
| 포트 사용 중 | 다른 프로그램이 점유 — 종료 후 재시도 |

[com0com]: https://com0com.sourceforge.net/
