"""Tiny in-app internationalization (KO/EN) with live language switching.

Widgets register a ``retranslate`` callback; calling :func:`set_language`
updates the language and invokes every callback so the UI re-labels itself
without a restart. Strings fall back to their key (and to English) if missing.
"""

from __future__ import annotations

from collections.abc import Callable

_STRINGS: dict[str, dict[str, str]] = {
    # generic
    "app.comm_title": {"en": "FAE Comm Tester", "ko": "FAE 통신 테스터"},
    "app.teaching_title": {"en": "TeachingManager", "ko": "TeachingManager (티칭 관리)"},
    "menu.language": {"en": "Language", "ko": "언어"},
    "lang.english": {"en": "English", "ko": "English"},
    "lang.korean": {"en": "한국어", "ko": "한국어"},
    "btn.connect": {"en": "Connect", "ko": "연결"},
    "btn.disconnect": {"en": "Disconnect", "ko": "연결 해제"},
    "btn.send": {"en": "Send", "ko": "송신"},
    "btn.clear": {"en": "Clear", "ko": "지우기"},
    "btn.save": {"en": "Save log…", "ko": "로그 저장…"},
    "btn.refresh": {"en": "Refresh", "ko": "새로고침"},
    "status.connected": {"en": "CONNECTED", "ko": "연결됨"},
    "status.disconnected": {"en": "DISCONNECTED", "ko": "연결 안 됨"},
    "status.listening": {"en": "LISTENING…", "ko": "수신 대기…"},
    # connection params
    "field.port": {"en": "Port", "ko": "포트"},
    "field.baud": {"en": "Baud rate", "ko": "통신 속도"},
    "field.databits": {"en": "Data bits", "ko": "데이터 비트"},
    "field.parity": {"en": "Parity", "ko": "패리티"},
    "field.stopbits": {"en": "Stop bits", "ko": "정지 비트"},
    "field.host": {"en": "Host", "ko": "호스트"},
    "field.tcp_port": {"en": "TCP port", "ko": "TCP 포트"},
    "field.mode": {"en": "Mode", "ko": "모드"},
    "field.local_port": {"en": "Local port", "ko": "로컬 포트"},
    "field.remote_host": {"en": "Remote host", "ko": "원격 호스트"},
    "field.remote_port": {"en": "Remote port", "ko": "원격 포트"},
    "field.interface": {"en": "Interface", "ko": "인터페이스"},
    "field.channel": {"en": "Channel", "ko": "채널"},
    "field.bitrate": {"en": "Bitrate", "ko": "비트레이트"},
    "field.can_id": {"en": "CAN ID (hex)", "ko": "CAN ID (16진)"},
    "mode.client": {"en": "Client", "ko": "클라이언트"},
    "mode.server": {"en": "Server (listen)", "ko": "서버 (수신대기)"},
    # groups
    "group.connection": {"en": "Connection", "ko": "연결 설정"},
    "group.send": {"en": "Send frame", "ko": "프레임 송신"},
    "group.monitor": {"en": "Monitor (TX / RX)", "ko": "모니터 (송신 / 수신)"},
    # send options
    "send.format": {"en": "Format", "ko": "형식"},
    "send.hex": {"en": "HEX", "ko": "HEX"},
    "send.ascii": {"en": "ASCII", "ko": "ASCII"},
    "send.append_crc": {"en": "Append Modbus CRC-16", "ko": "Modbus CRC-16 자동첨부"},
    "send.append_newline": {"en": "Append CR+LF", "ko": "CR+LF 추가"},
    "send.periodic": {"en": "Repeat every", "ko": "주기 반복"},
    "send.ms": {"en": "ms", "ko": "ms"},
    "send.placeholder_hex": {"en": "e.g. 01 03 00 00 00 0A", "ko": "예: 01 03 00 00 00 0A"},
    "send.placeholder_ascii": {"en": "type text to send", "ko": "보낼 텍스트 입력"},
    # monitor options
    "monitor.show_hex": {"en": "HEX", "ko": "HEX"},
    "monitor.show_ascii": {"en": "ASCII", "ko": "ASCII"},
    "monitor.timestamp": {"en": "Timestamps", "ko": "타임스탬프"},
    "monitor.autoscroll": {"en": "Auto-scroll", "ko": "자동 스크롤"},
    "monitor.decode_modbus": {"en": "Decode Modbus", "ko": "Modbus 해석"},
    # tabs
    "tab.serial": {"en": "Serial (RS-232/485)", "ko": "Serial (RS-232/485)"},
    "tab.tcp": {"en": "TCP/IP", "ko": "TCP/IP"},
    "tab.udp": {"en": "UDP", "ko": "UDP"},
    "tab.can": {"en": "CAN", "ko": "CAN"},
    # saved frames (macros)
    "group.macros": {"en": "Saved frames", "ko": "저장된 프레임"},
    "macro.save_current": {"en": "Save current…", "ko": "현재 저장…"},
    "macro.delete": {"en": "Delete", "ko": "삭제"},
    "macro.apply": {"en": "Load", "ko": "불러오기"},
    "macro.all_groups": {"en": "(all makers)", "ko": "(전체 제조사)"},
    "macro.no_group": {"en": "(ungrouped)", "ko": "(그룹 없음)"},
    "macro.name_title": {"en": "Save frame", "ko": "프레임 저장"},
    "macro.name_prompt": {"en": "Name:", "ko": "이름:"},
    "macro.group_prompt": {"en": "Group / maker (optional):", "ko": "그룹 / 제조사 (선택):"},
    # presets
    "preset.label": {"en": "Preset", "ko": "프리셋"},
    "preset.none": {"en": "(none)", "ko": "(없음)"},
    "preset.modbus_read": {"en": "Modbus: Read Holding Regs", "ko": "Modbus: 홀딩레지스터 읽기"},
    "preset.apply": {"en": "Insert", "ko": "삽입"},
    # TeachingManager
    "tm.group_project": {"en": "Project", "ko": "프로젝트"},
    "tm.group_validation": {"en": "Validation / log", "ko": "검증 / 로그"},
    "tm.btn_sample": {"en": "Sample", "ko": "샘플"},
    "tm.btn_open": {"en": "Open…", "ko": "열기…"},
    "tm.btn_save": {"en": "Save…", "ko": "저장…"},
    "tm.btn_export": {"en": "Export CSV…", "ko": "CSV 내보내기…"},
    "tm.btn_add": {"en": "Add point", "ko": "포인트 추가"},
    "tm.btn_delete": {"en": "Delete point", "ko": "포인트 삭제"},
    "tm.btn_validate": {"en": "Validate", "ko": "검증"},
    "tm.map_title": {"en": "Teaching map (mm)", "ko": "티칭 맵 (mm)"},
    # table columns
    "tm.col_id": {"en": "id", "ko": "번호"},
    "tm.col_name": {"en": "name", "ko": "이름"},
    "tm.col_type": {"en": "type", "ko": "설비 종류"},
    "tm.col_x": {"en": "x (mm)", "ko": "x (mm)"},
    "tm.col_y": {"en": "y (mm)", "ko": "y (mm)"},
    "tm.col_theta": {"en": "θ (°)", "ko": "θ (°)"},
    "tm.col_station": {"en": "station", "ko": "설비 ID"},
    "tm.col_status": {"en": "status", "ko": "상태"},
    "tm.col_color": {"en": "color", "ko": "색상"},
    "tm.col_shape": {"en": "shape", "ko": "모양"},
    # status
    "tm.status_in_progress": {"en": "In progress", "ko": "진행중"},
    "tm.status_done": {"en": "Done", "ko": "완료"},
    "tm.status_alarm": {"en": "Alarm", "ko": "알람"},
    # dashboard
    "tm.dash_total": {"en": "Total", "ko": "전체"},
    # bottom tabs
    "tm.tab_background": {"en": "Background (CAD)", "ko": "배경 도면 (CAD)"},
    "tm.tab_types": {"en": "Equipment types", "ko": "설비 종류"},
    "tm.tab_log": {"en": "Log", "ko": "로그"},
    # background
    "tm.bg_load": {"en": "Load image…", "ko": "이미지 불러오기…"},
    "tm.bg_clear": {"en": "Clear", "ko": "제거"},
    "tm.bg_opacity": {"en": "Opacity", "ko": "투명도"},
    "tm.bg_scale": {"en": "Scale (mm/px)", "ko": "축척 (mm/픽셀)"},
    "tm.bg_none": {"en": "(no background)", "ko": "(배경 없음)"},
    "tm.bg_hint": {
        "en": "Load a floor plan / CAD export (PNG/JPG/BMP) and teach points on top of it.",
        "ko": "도면/CAD(PNG·JPG·BMP)을 불러와 그 위에 포인트를 티칭하세요.",
    },
    # equipment types editor
    "tm.types_add": {"en": "Add type", "ko": "종류 추가"},
    "tm.types_remove": {"en": "Remove", "ko": "삭제"},
    "tm.types_new_prompt": {"en": "New equipment type name:", "ko": "새 설비 종류 이름:"},
    # shapes
    "tm.shape_circle": {"en": "circle", "ko": "원"},
    "tm.shape_square": {"en": "square", "ko": "사각형"},
    "tm.shape_triangle": {"en": "triangle", "ko": "삼각형"},
    "tm.shape_diamond": {"en": "diamond", "ko": "마름모"},
    "tm.shape_star": {"en": "star", "ko": "별"},
    "tm.shape_plus": {"en": "plus", "ko": "플러스"},
    "tm.shape_cross": {"en": "cross", "ko": "엑스"},
}


class _I18N:
    def __init__(self) -> None:
        self.language = "en"
        self._subscribers: list[Callable[[], None]] = []

    def tr(self, key: str) -> str:
        entry = _STRINGS.get(key)
        if not entry:
            return key
        return entry.get(self.language) or entry.get("en") or key

    def set_language(self, language: str) -> None:
        if language not in ("en", "ko") or language == self.language:
            return
        self.language = language
        for callback in list(self._subscribers):
            try:
                callback()
            except RuntimeError:
                # The owning widget was destroyed; drop its callback.
                self._subscribers.remove(callback)

    def subscribe(self, callback: Callable[[], None]) -> None:
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)


i18n = _I18N()


def tr(key: str) -> str:
    """Translate *key* into the current language."""
    return i18n.tr(key)
