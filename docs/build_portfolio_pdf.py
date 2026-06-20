"""Generate a submission-ready PDF portfolio (Korean) for the AMHS / IT role.

Renders an HTML document (with embedded screenshots) to an A4 PDF via Qt's
QTextDocument + QPdfWriter, so it works offline and embeds Korean fonts.

    QT_QPA_PLATFORM=offscreen PYTHONPATH=src python docs/build_portfolio_pdf.py
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMarginsF, QSizeF, QUrl  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QFont,
    QImage,
    QPageLayout,
    QPageSize,
    QPdfWriter,
    QTextDocument,
)
from PySide6.QtWidgets import QApplication  # noqa: E402

OUT = "docs/Portfolio_SangbongLee_AMHS.pdf"

GITHUB = "https://github.com/bong7233/FAE_Toolkit_Bong"
RELEASES = GITHUB + "/releases"
SITE = "https://bongfae-production.up.railway.app/#about"

NAVY = "#16335c"
BLUE = "#1f6feb"
LIGHT = "#eef2f7"

# Screenshots embedded as named resources.
IMAGES = {
    "img_teaching": "docs/screenshot_teaching.png",
    "img_teaching_types": "docs/screenshot_teaching_types.png",
    "img_comm": "docs/screenshot_comm_tcp.png",
}


def _h2(text: str) -> str:
    return (
        f'<h2 style="color:{NAVY}; font-size:13pt; margin-top:16px; '
        f'border-bottom:2px solid {BLUE};">{text}</h2>'
    )


def _build_html() -> str:
    head = f"""
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr><td>
        <span style="font-size:21pt; color:{NAVY};"><b>산업 통신 테스트 &amp; AGV/AMR 티칭 자동화 툴킷</b></span><br/>
        <span style="font-size:11pt; color:#5a6675;">FAE Toolkit · 크로스플랫폼(Windows·Linux) 데스크톱 도구 · Python / C++</span>
      </td></tr>
    </table>
    <table width="100%" cellpadding="6" cellspacing="0" border="0" style="margin-top:8px;">
      <tr>
        <td bgcolor="{NAVY}" width="50%"><font color="#ffffff">
          <b>이상봉 (Sangbong Lee)</b><br/>batmantwo7233@gmail.com
        </font></td>
        <td bgcolor="{BLUE}" width="50%"><font color="#ffffff">
          <b>지원 직무 · IT (AMHS)</b><br/>AMHS 구축 / 제어 / 소프트웨어 개발
        </font></td>
      </tr>
    </table>
    <table width="100%" cellpadding="4" cellspacing="0" border="0">
      <tr><td bgcolor="{LIGHT}" style="font-size:9pt;">
        <b>GitHub</b> {GITHUB} &nbsp;·&nbsp; <b>Releases(실행파일)</b> {RELEASES} &nbsp;·&nbsp; <b>Portfolio</b> {SITE}
      </td></tr>
    </table>
    """

    summary = f"""
    {_h2("한 줄 소개")}
    <table width="100%" cellpadding="8" cellspacing="0" border="0">
      <tr><td bgcolor="{LIGHT}">
        반송설비(<b>OHT·AMR</b>)와 상위 제어(<b>MCS</b>) 사이의 <b>산업 통신을 직접 테스트·진단</b>하고
        (Serial·TCP·UDP·CAN·Modbus), 반송차 <b>티칭 포인트를 도면 위에서 관리</b>하는 크로스플랫폼 도구를
        직접 설계·구현하여 <b>자동화 테스트·CI/CD로 검증·배포</b>했습니다.
      </td></tr>
    </table>
    {_h2("핵심 역량")}
    <ul>
      <li>산업 통신 4종(Serial/TCP/UDP/CAN) + <b>Modbus-RTU·CRC-16 무의존 자체 구현</b>, 수신 프레임 디코더</li>
      <li>반송차 티칭 관리툴 — <b>CAD 도면 배경 위 티칭</b>, 설비 종류별 색·모양, <b>상태(완료/진행중/알람) 관리</b></li>
      <li>품질 — 자동화 테스트 <b>87개</b> + 정적분석(ruff) + GitHub Actions <b>Windows·Linux CI 매트릭스</b></li>
      <li>배포 — 태그 푸시 시 Win·Linux <b>실행파일 자동 빌드·릴리스(CD)</b>, C++(pybind11)·ROS 2 연계</li>
    </ul>
    """

    fit = f"""
    {_h2("직무 적합성 — AMHS / OHT·AMR")}
    <p>Zenix Robotics에서 <b>AGV/AMR 물류 로봇</b>의 운영·소프트웨어를 다루며 OHT/AMR의 H/W·S/W 동작을
    이해했습니다. 본 프로젝트는 그 경험을 바탕으로 <b>‘반송설비 통신 인터페이스 디버깅’</b>과
    <b>‘반송차 티칭·커미셔닝’</b>을 직접 도구로 구현하여, AMHS 구축·제어·SW 개발 직무에 필요한 역량을
    <b>코드와 동작하는 결과물</b>로 증명합니다.</p>
    """

    arch = f"""
    {_h2("아키텍처")}
    <table width="100%" cellpadding="7" cellspacing="3" border="0">
      <tr>
        <td bgcolor="{BLUE}" width="50%"><font color="#ffffff"><b>앱 1 · Comm Tester</b><br/>
          Serial·TCP·UDP·CAN 탭 / 프레임 빌더(HEX·ASCII·CRC·주기) / 모니터(TX·RX) / Modbus 디코더 / 저장 프레임</font></td>
        <td bgcolor="#2c9c7a" width="50%"><font color="#ffffff"><b>앱 2 · TeachingManager</b><br/>
          포인트 표 + 2D 맵 / CAD 도면 배경 / 티칭 상태 / 설비 종류 커스텀 / JSON·CSV</font></td>
      </tr>
      <tr><td bgcolor="{LIGHT}" colspan="2"><b>Transport 계층(공통 인터페이스)</b> —
        SerialTransport(pyserial) · Tcp/Udp Transport(socket) · CanTransport(python-can)</td></tr>
      <tr><td bgcolor="{LIGHT}" colspan="2"><b>라이브러리 / CLI</b> —
        Modbus-RTU·CRC-16 자체 구현 · BMS/IO/CAN 디바이스 에뮬레이터</td></tr>
      <tr><td bgcolor="#dfe6ee" colspan="2"><b>공통 기반</b> —
        C++17 코어(pybind11) · ROS 2 브리지 · GitHub Actions CI/CD(Windows+Linux)</td></tr>
    </table>
    """

    teaching = f"""
    {_h2("핵심 기능 ① — TeachingManager (반송차 티칭)")}
    <p style="font-size:9.5pt; color:#5a6675;">OHT/AMR 티칭 포인트를 <b>CAD 도면 위</b>에서 관리.
    설비 종류별 색·모양, 티칭 <b>상태(완료/진행중/알람)</b> 대시보드, JSON/CSV 입출력.</p>
    <img src="img_teaching" width="640"/>
    <img src="img_teaching_types" width="640"/>
    """

    comm = f"""
    {_h2("핵심 기능 ② — Comm Tester (장비-호스트 통신)")}
    <p style="font-size:9.5pt; color:#5a6675;">장비·반송차 통신 인터페이스 테스트. HEX/ASCII 프레임 직접
    입력·송수신, <b>Modbus 디코더</b>(요청/응답/CRC 해석), 제조사별 프레임 저장(매크로).</p>
    <img src="img_comm" width="640"/>
    """

    stack = f"""
    {_h2("기술 스택 · 검증 · 배포")}
    <table width="100%" cellpadding="6" cellspacing="0" border="1" bordercolor="#cfd8e3">
      <tr><td bgcolor="{LIGHT}" width="22%"><b>언어/런타임</b></td>
          <td>Python 3.10+ (PySide6) · C++17 / CMake + pybind11</td></tr>
      <tr><td bgcolor="{LIGHT}"><b>통신</b></td>
          <td>pyserial(RS-232/485) · socket(TCP/UDP) · python-can(CAN) · Modbus-RTU(자체 구현)</td></tr>
      <tr><td bgcolor="{LIGHT}"><b>품질 / CI</b></td>
          <td>pytest(87 통과) · ruff · GitHub Actions 매트릭스(Windows+Linux · C++ · pybind11 · ROS 2)</td></tr>
      <tr><td bgcolor="{LIGHT}"><b>배포 / CD</b></td>
          <td>PyInstaller 단독 실행파일(Win/Linux) — 버전 태그 시 릴리스에 자동 첨부</td></tr>
    </table>
    """

    mapping = f"""
    {_h2("AMHS(IT) 직무 역량 매핑")}
    <table width="100%" cellpadding="6" cellspacing="0" border="1" bordercolor="#cfd8e3">
      <tr><td bgcolor="{NAVY}" width="40%"><font color="#ffffff"><b>직무 요구 역량</b></font></td>
          <td bgcolor="{NAVY}"><font color="#ffffff"><b>본 포트폴리오에서의 근거</b></font></td></tr>
      <tr><td><b>OHT/AMR H/W·S/W 이해</b></td>
          <td>AGV/AMR 물류로봇 운영·SW 경력 + 반송차 티칭 관리툴(TeachingManager) 직접 개발</td></tr>
      <tr><td bgcolor="{LIGHT}"><b>반송설비 통신·인터페이스</b></td>
          <td bgcolor="{LIGHT}">Serial(232/485)·TCP/IP·CAN·Modbus 통신 테스터 구현, 프레임 디코더로 송수신 해석</td></tr>
      <tr><td><b>AMHS 제어 / SW 개발</b></td>
          <td>Python/C++ 크로스플랫폼 SW, Transport 추상화 설계, ROS 2 브리지(로봇 제어 연계)</td></tr>
      <tr><td bgcolor="{LIGHT}"><b>양산 SW 품질·신뢰성</b></td>
          <td bgcolor="{LIGHT}">자동화 테스트 87 + CI(Win/Linux) + 실행파일 자동 빌드·배포로 재현성 확보</td></tr>
      <tr><td><b>현장 디버깅 / 장애 대응</b></td>
          <td>가상 시리얼·디바이스 에뮬레이터로 HW 없이 재현, 송수신 모니터·CRC 검증</td></tr>
    </table>
    <p style="font-size:9pt; color:#5a6675; margin-top:14px;">
      전체 소스·문서(국문/영문)·실행파일: {GITHUB}
    </p>
    """

    return (
        f"<html><body>{head}{summary}{fit}{arch}{teaching}{comm}{stack}{mapping}</body></html>"
    )


def main() -> int:
    app = QApplication.instance() or QApplication([])  # noqa: F841

    writer = QPdfWriter(OUT)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(14, 14, 14, 14), QPageLayout.Unit.Millimeter)
    writer.setResolution(96)

    doc = QTextDocument()
    doc.setDefaultFont(QFont("Noto Sans CJK KR", 10))
    for name, path in IMAGES.items():
        img = QImage(path)
        if img.isNull():
            print(f"WARNING: missing image {path}")
            continue
        doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(name), img)
    doc.setHtml(_build_html())
    doc.setPageSize(QSizeF(writer.pageLayout().paintRectPixels(writer.resolution()).size()))
    doc.print_(writer)

    size_kb = os.path.getsize(OUT) // 1024
    print(f"saved {OUT} ({size_kb} KiB, {doc.pageCount()} pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
