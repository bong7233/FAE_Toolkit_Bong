# 포트폴리오 가이드 (Portfolio)

> 🌐 **한국어** (기본) · [English](PORTFOLIO.en.md) · [⬅ README](../README.md)

이 프로젝트를 **FAE(Field Application Engineer) 이직용 포트폴리오**로 제출·발표할 때를 위한 안내입니다.
"무엇을 보여주고, 어떻게 설명하고, 어디에 링크할지"를 정리했습니다.

---

## 1. 한 줄 소개

> 산업용 장비(BMS·원격 IO·AGV)를 **Serial/TCP/UDP/CAN으로 직접 통신·진단**하는 크로스플랫폼 도구를
> 직접 설계·구현하고, **테스트·CI/CD·실행파일 자동배포**까지 갖춘 프로젝트.

## 2. 링크 모음 (이력서/포트폴리오에 넣기)

| 항목 | 링크 |
|---|---|
| GitHub 저장소 | https://github.com/bong7233/FAE_Toolkit_Bong |
| 다운로드(실행파일) | https://github.com/bong7233/FAE_Toolkit_Bong/releases |
| CI 상태 | 저장소 상단 **CI 배지** (자동 빌드/테스트 통과 증명) |
| 개인 포트폴리오 | https://bongfae-production.up.railway.app/#about |

---

## 3. 이 프로젝트가 증명하는 것 (FAE 직무 연관성)

FAE는 **현장에서 장비가 왜 통신이 안 되는지**를 짚고, 고객사 엔지니어에게 설명·지원하는 역할입니다.
이 프로젝트는 그 핵심 역량을 코드로 보여줍니다.

| FAE 현업 역량 | 이 프로젝트에서 보여주는 근거 |
|---|---|
| 산업 통신 프로토콜 이해 | Modbus-RTU·CRC-16 **직접 구현**, 프레임 디코더 |
| 현장 디버깅 도구 사용/제작 | Hercules/Docklight류 **통신 테스터를 직접 제작** |
| 다양한 물리계층 대응 | RS-232/485(Serial), TCP/UDP, CAN 모두 지원 |
| 제조사별 차이 대응 | 프레임을 **사용자가 직접 정의**하고 매크로로 저장 |
| 재현성·신뢰성 | 자동 테스트 + CI(Win/Linux) + 하드웨어 없는 시연 |
| 크로스플랫폼 배포 | 단독 실행파일 자동 빌드(Win/Linux) |
| 로봇/AGV 도메인 | TeachingManager(티칭 포인트), 로봇 S/W 경력 연계 |

---

## 4. 데모 시나리오 (면접/발표용, 3~5분)

하드웨어가 없어도 노트북 한 대로 시연 가능합니다.

1. **연결 실패부터 보여주기** — Serial 탭에서 빈 포트로 *Connect* → **실패**.
   → "가짜 값이 아니라 실제 통신을 다룬다"는 점을 강조.
2. **가상 페어 + 에뮬레이터로 실제 송수신** ([USAGE](USAGE.md) 6장)
   ```bash
   socat -d -d PTY,link=/tmp/ttyA,raw,echo=0 PTY,link=/tmp/ttyB,raw,echo=0
   fae-toolkit bms-sim-serve --port /tmp/ttyA --baudrate 115200
   ```
   Comm Tester에서 `/tmp/ttyB` 연결 → 저장 프레임 *"Read pack V/I/SOC block"* 불러오기 → **Send**.
3. **모니터 + Modbus 디코드** — *Decode Modbus* 체크 → 송신은 요청, 수신은 응답(레지스터/CRC)으로 해석되는 것을 보여주기.
4. **TeachingManager** — 샘플 불러오기 → 포인트 검증 → 2D 맵 확인.
5. **CI/실행파일** — GitHub의 초록 CI 배지와 Releases의 Win/Linux 실행파일을 보여주며 "푸시하면 자동 빌드·배포"를 설명.

---

## 5. 기술 어필 체크리스트

- [x] 통신 4종(Serial/TCP/UDP/CAN) 단일 아키텍처(Transport 추상화)로 통합
- [x] 프로토콜(Modbus/CRC) **의존 라이브러리 없이 직접 구현** → 바이트 레벨 이해 증명
- [x] 수신 프레임 디코더(요청/응답/예외/CRC 해석)
- [x] 한/영 i18n(실시간 전환)
- [x] 자동 테스트(pytest) + 정적분석(ruff)
- [x] GitHub Actions로 Windows·Linux **매트릭스 CI** + 실행파일 **CD**
- [x] C++17 코어 + pybind11(언어 간 동일성 검증)
- [x] ROS 2 브릿지(로봇 생태계 연계)
- [x] 하드웨어 없이도 **정직하게** 시연(에뮬레이터/가상 페어)

---

## 6. 제출 방법

1. **저장소 공개 확인** — 이미 public. README(한글 기본 + English)가 첫 화면.
2. **이력서/경력기술서**에 위 [링크 모음](#2-링크-모음-이력서포트폴리오에-넣기) 삽입.
   - 추천 문구: *"산업 통신 테스트 도구를 직접 설계·구현(Python/C++), CI/CD로 Win·Linux 실행파일 자동 배포"*
3. **실행파일 첨부가 필요하면** Releases 링크를 안내하거나, [DEVELOPMENT 7장](DEVELOPMENT.md)으로 새 버전을 빌드.
4. **개인 포트폴리오 사이트**에 GitHub/Releases 링크와 데모 GIF(`docs/demo_comm.gif`)를 함께 게시.

---

## 7. 예상 질문 & 답변 포인트

| 질문 | 답변 방향 |
|---|---|
| "왜 직접 만들었나?" | 기성 툴(Docklight 등)은 제조사별 프레임·디코드·배포를 한 번에 못 한다 → 현장 요구를 반영 |
| "CRC를 왜 직접 구현?" | 라이브러리 의존을 줄이고 **바이트 흐름을 정확히 이해/문서화**하기 위해 |
| "하드웨어 없이 어떻게 검증?" | 가상 시리얼 페어 + 디바이스 에뮬레이터로 **실제 pyserial 경로** 그대로 시험, CI에서 자동화 |
| "테스트/CI는?" | pytest + ruff, Win/Linux 매트릭스, 태그 시 실행파일 자동 빌드·첨부 |
| "확장성은?" | Transport 추상화로 새 통신 추가 용이, i18n·매크로로 현장 맞춤 |

---

## 8. 더 다듬고 싶다면 (로드맵)

README의 **로드맵** 참고. 다음 후보:
- 프레임 시퀀스(시나리오) 자동 송신
- 장비별 프레임 라이브러리 확장
- 응답 파형/타이밍 시각화
