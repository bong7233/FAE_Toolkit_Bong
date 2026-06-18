"""TeachingManager main window (standalone app)."""

from __future__ import annotations

from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import QMainWindow

from fae_toolkit import __version__
from fae_toolkit.teaching_manager.view import TeachingView
from fae_toolkit.ui.i18n import i18n, tr


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.resize(1100, 680)
        self.view = TeachingView()
        self.setCentralWidget(self.view)
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

    def retranslate(self) -> None:
        self.setWindowTitle(f"{tr('app.teaching_title')}  v{__version__}")
        self._lang_menu.setTitle(tr("menu.language"))

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self.view.shutdown()
        super().closeEvent(event)
