# Portfolio

> 🌐 [한국어](PORTFOLIO.md) (default) · **English** · [⬅ README](../README.en.md)

This is a guide for when you submit or present this project as a **portfolio for an FAE (Field Application Engineer) job change**.
It organizes "what to show, how to explain it, and where to link it."

---

## 1. One-Line Pitch

> A cross-platform tool that **directly communicates with and diagnoses** industrial equipment (BMS · remote IO · AGV) **over Serial/TCP/UDP/CAN**,
> designed and implemented from scratch, complete with **testing · CI/CD · automatic executable deployment**.

## 2. Links (for resume/portfolio)

| Item | Link |
|---|---|
| GitHub repository | https://github.com/bong7233/FAE_Toolkit_Bong |
| Download (executables) | https://github.com/bong7233/FAE_Toolkit_Bong/releases |
| CI status | **CI badge** at the top of the repository (proof that automated build/test passes) |
| Personal portfolio | https://bongfae-production.up.railway.app/#about |

---

## 3. What This Project Proves (relevance to the FAE role)

An FAE is responsible for pinpointing **why equipment fails to communicate in the field** and explaining/supporting customer engineers.
This project demonstrates that core competency in code.

| FAE on-the-job competency | Evidence shown in this project |
|---|---|
| Understanding industrial communication protocols | **Custom implementation** of Modbus-RTU·CRC-16, frame decoder |
| Using/building field debugging tools | **Built a communication tester** of the Hercules/Docklight kind from scratch |
| Handling diverse physical layers | Supports RS-232/485 (Serial), TCP/UDP, and CAN |
| Handling per-vendor differences | **User-defined** frames saved as macros |
| Reproducibility·reliability | Automated tests + CI (Win/Linux) + hardware-free demo |
| Cross-platform deployment | Automatic standalone executable builds (Win/Linux) |
| Robot/AGV domain | TeachingManager (teaching points), tied to robot S/W experience |

---

## 4. Demo Scenario (for interviews/presentations, 3–5 min)

You can demo with a single laptop even without hardware.

1. **Start by showing a connection failure** — on the Serial tab, *Connect* to an empty port → **fail**.
   → Emphasize that "this handles real communication, not fake values."
2. **Real TX/RX with a virtual pair + emulator** ([USAGE](USAGE.en.md) section 6)
   ```bash
   socat -d -d PTY,link=/tmp/ttyA,raw,echo=0 PTY,link=/tmp/ttyB,raw,echo=0
   fae-toolkit bms-sim-serve --port /tmp/ttyA --baudrate 115200
   ```
   In Comm Tester, connect `/tmp/ttyB` → load the saved frame *"Read pack V/I/SOC block"* → **Send**.
3. **Monitor + Modbus decode** — check *Decode Modbus* → show that TX is interpreted as a request and RX as a response (register/CRC).
4. **TeachingManager** — load the sample → validate points → check the 2D map.
5. **CI/executables** — show GitHub's green CI badge and the Win/Linux executables in Releases, explaining "push and it builds/deploys automatically."

---

## 5. Technical Appeal Checklist

- [x] Four communication types (Serial/TCP/UDP/CAN) unified under a single architecture (Transport abstraction)
- [x] Protocols (Modbus/CRC) **implemented from scratch with no dependent libraries** → proof of byte-level understanding
- [x] Received-frame decoder (request/response/exception/CRC interpretation)
- [x] KO/EN i18n (real-time switching)
- [x] Automated tests (pytest) + static analysis (ruff)
- [x] **Matrix CI** on Windows·Linux via GitHub Actions + executable **CD**
- [x] C++17 core + pybind11 (cross-language parity verification)
- [x] ROS 2 bridge (integration with the robotics ecosystem)
- [x] **Honest** demo even without hardware (emulator/virtual pair)

---

## 6. How to Submit

1. **Confirm the repository is public** — already public. The README (Korean default + English) is the landing screen.
2. Insert the [Links](#2-links-for-resumeportfolio) above into your **resume/CV**.
   - Suggested phrasing: *"Designed and implemented an industrial communication testing tool from scratch (Python/C++), with automatic Win·Linux executable deployment via CI/CD."*
3. **If executable attachments are needed**, point to the Releases link, or build a new version via [DEVELOPMENT section 7](DEVELOPMENT.en.md).
4. On your **personal portfolio site**, post the GitHub/Releases links together with the demo GIF (`docs/demo_comm.gif`).

---

## 7. Anticipated Questions & Answer Points

| Question | Answer direction |
|---|---|
| "Why build it yourself?" | Off-the-shelf tools (Docklight, etc.) can't do per-vendor frames·decode·deployment all at once → reflects field needs |
| "Why implement CRC yourself?" | To reduce library dependence and **accurately understand/document the byte flow** |
| "How do you verify without hardware?" | Test the **real pyserial path** as-is with a virtual serial pair + device emulator, automated in CI |
| "What about testing/CI?" | pytest + ruff, Win/Linux matrix, automatic executable build·attach on tag |
| "What about extensibility?" | The Transport abstraction makes adding new communication easy; i18n·macros customize it for the field |

---

## 8. If You Want to Polish Further (roadmap)

See the **Roadmap** in the README. Next candidates:
- Automatic transmission of frame sequences (scenarios)
- Expanding the per-device frame library
- Response waveform/timing visualization
