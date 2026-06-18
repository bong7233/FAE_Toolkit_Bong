# Real Hardware Integration Guide (Hardware guide)

> 🌐 [한국어](HARDWARE.md) (default) · **English** · [⬅ README](../README.en.md)

This toolkit connects directly to **real serial ports (pyserial)** and **real CAN interfaces (python-can)**.
The simulator + loopback are for developing/evaluating without hardware, and the methods below let you
validate the real port path. (The `bms-sim-serve` ↔ `bms-demo` combination matches the flow validated by CI's `test_serial_socat`.)

---

## 1. Real Serial Ports (RS-232 / RS-485)

### Linux
```bash
# check ports
dmesg | grep tty            # usually /dev/ttyUSB0, /dev/ttyACM0
sudo usermod -aG dialout $USER   # permissions (re-login required)

# poll a BMS (Modbus)
fae-toolkit bms-demo --port /dev/ttyUSB0 --baudrate 9600 --unit 1
```

### Windows
```powershell
# find the COM number in Device Manager → Ports (COM & LPT)
fae-toolkit bms-demo --port COM3 --baudrate 9600 --unit 1
```

## 2. Testing the "Real Port Path" Without Hardware (virtual serial pair)

Create a virtual serial pair, bring up a **simulator as the device** on one side, then connect with the app on the other side,
and it operates over the **same pyserial code path** as real RS-232/485.

### Linux (socat)
```bash
socat -d -d PTY,link=/tmp/ttyA,raw,echo=0 PTY,link=/tmp/ttyB,raw,echo=0
# Terminal 1 — serve the simulator as a device on /tmp/ttyA
fae-toolkit bms-sim-serve --port /tmp/ttyA --baudrate 115200
# Terminal 2 — connect the app to /tmp/ttyB
fae-toolkit bms-demo --port /tmp/ttyB --baudrate 115200
```

### Windows (com0com)
1. After installing [com0com], create a `COM4 <-> COM5` virtual pair
2. `fae-toolkit bms-sim-serve --port COM4 --baudrate 115200`
3. `fae-toolkit bms-demo --port COM5 --baudrate 115200`

> `bms-sim-serve` brings up a **Modbus-RTU slave (a fake BMS)** on the port. It can be polled not only by our app but also
> by any Modbus master tool (e.g., modpoll), making it useful as a dummy for debugging other software too.

## 3. CAN

### Virtual (no hardware required)
```bash
fae-toolkit can-demo            # python-can 'virtual' bus
```

### Real CAN (Linux, SocketCAN)
```bash
sudo ip link set can0 type can bitrate 500000
sudo ip link set up can0
fae-toolkit can-demo --interface socketcan --channel can0
```

### Real CAN (Windows)
PCAN / Kvaser, etc., are specified as python-can interfaces.
```powershell
fae-toolkit can-demo --interface pcan --channel PCAN_USBBUS1
```

## 4. Troubleshooting

| Symptom | Check |
|------|------|
| No response (timeout) | baud rate / unit id / wiring (A-B, TX-RX) / termination resistor (RS-485) |
| CRC error | noise, wrong baud rate, grounding |
| Permission error (Linux) | `dialout` group, whether the port is occupied (`lsof <port>`) |
| Port in use | another program is occupying it — close it and retry |

[com0com]: https://com0com.sourceforge.net/
