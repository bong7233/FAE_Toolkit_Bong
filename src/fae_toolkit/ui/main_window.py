"""FAE Comm Tester — transport-centric main window (Serial / TCP / UDP / CAN)."""

from __future__ import annotations

from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import QMainWindow, QTabWidget

from fae_toolkit import __version__
from fae_toolkit.ui.comm.bytestream_tab import ByteStreamTab
from fae_toolkit.ui.comm.can_tab import CanTab
from fae_toolkit.ui.comm.panels import SerialPanel, TcpPanel, UdpPanel
from fae_toolkit.ui.i18n import i18n, tr


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.resize(1100, 680)

        self.serial_tab = ByteStreamTab(SerialPanel())
        self.tcp_tab = ByteStreamTab(TcpPanel())
        self.udp_tab = ByteStreamTab(UdpPanel())
        self.can_tab = CanTab()
        self._tabs = QTabWidget()
        self._tabs.addTab(self.serial_tab, "")
        self._tabs.addTab(self.tcp_tab, "")
        self._tabs.addTab(self.udp_tab, "")
        self._tabs.addTab(self.can_tab, "")
        self.setCentralWidget(self._tabs)

        self._build_menu()
        i18n.subscribe(self.retranslate)
        self.retranslate()

    def _build_menu(self) -> None:
        self._lang_menu = self.menuBar().addMenu("")
        group = QActionGroup(self)
        self._act_en = self._lang_menu.addAction("English")
        self._act_ko = self._lang_menu.addAction("한국어")
        for act, lang in ((self._act_en, "en"), (self._act_ko, "ko")):
            act.setCheckable(True)
            act.setChecked(i18n.language == lang)
            group.addAction(act)
            act.triggered.connect(lambda _checked=False, lng=lang: i18n.set_language(lng))

    @property
    def tabs(self) -> list:
        return [self.serial_tab, self.tcp_tab, self.udp_tab, self.can_tab]

    def retranslate(self) -> None:
        self.setWindowTitle(f"{tr('app.comm_title')}  v{__version__}")
        self._tabs.setTabText(0, tr("tab.serial"))
        self._tabs.setTabText(1, tr("tab.tcp"))
        self._tabs.setTabText(2, tr("tab.udp"))
        self._tabs.setTabText(3, tr("tab.can"))
        self._lang_menu.setTitle(tr("menu.language"))

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        for tab in self.tabs:
            tab.shutdown()
        super().closeEvent(event)
