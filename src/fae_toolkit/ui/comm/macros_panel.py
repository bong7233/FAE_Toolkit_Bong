"""Saved-frame (macro) panel: store per-maker frames and recall them.

A thin GUI shell over :class:`fae_toolkit.core.macros.MacroStore`.  It captures
the current frame-sender state, persists it to disk, and loads any saved frame
back into the sender on demand.  The store logic is Qt-free and tested
separately; the helper methods here (``_save_named`` / ``_apply_name`` /
``_delete_selected``) are written so tests can drive them without dialogs.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from fae_toolkit.core.macros import Macro, MacroStore, default_macros, default_store_path
from fae_toolkit.ui.comm.sender import FrameSenderWidget
from fae_toolkit.ui.i18n import i18n, tr


class MacroPanel(QGroupBox):
    def __init__(self, sender: FrameSenderWidget, store_path: Path | str | None = None) -> None:
        super().__init__()
        self._sender = sender
        self._path = Path(store_path) if store_path is not None else default_store_path()

        existed = self._path.exists()
        self._store = MacroStore.load(self._path)
        if not existed and len(self._store) == 0:
            for macro in default_macros():
                self._store.add(macro)
            self._persist()

        self._build()
        i18n.subscribe(self.retranslate)
        self.retranslate()
        self._reload_groups()
        self._reload_list()

    def _build(self) -> None:
        layout = QVBoxLayout(self)

        self.group_combo = QComboBox()
        self.group_combo.currentIndexChanged.connect(self._reload_list)
        layout.addWidget(self.group_combo)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _it: self._apply_selected())
        layout.addWidget(self.list, stretch=1)

        row = QHBoxLayout()
        self.btn_save = QPushButton()
        self.btn_save.clicked.connect(self._save_current)
        self.btn_apply = QPushButton()
        self.btn_apply.clicked.connect(self._apply_selected)
        self.btn_delete = QPushButton()
        self.btn_delete.clicked.connect(self._delete_selected)
        for b in (self.btn_save, self.btn_apply, self.btn_delete):
            row.addWidget(b)
        layout.addLayout(row)

    # --- persistence ------------------------------------------------------ #
    def _persist(self) -> None:
        try:
            self._store.save(self._path)
        except OSError:
            pass  # read-only home in CI; in-memory store still works this session

    # --- list / group population ------------------------------------------ #
    def _selected_group(self) -> str | None:
        return self.group_combo.currentData()

    def _reload_groups(self) -> None:
        current = self._selected_group()
        self.group_combo.blockSignals(True)
        self.group_combo.clear()
        self.group_combo.addItem(tr("macro.all_groups"), None)
        for group in self._store.groups():
            label = group if group else tr("macro.no_group")
            self.group_combo.addItem(label, group)
        idx = self.group_combo.findData(current)
        self.group_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.group_combo.blockSignals(False)

    def _reload_list(self) -> None:
        self.list.clear()
        for macro in self._store.filter(self._selected_group()):
            item = QListWidgetItem(macro.name)
            item.setData(Qt.UserRole, macro.name)
            tip = f"[{macro.group or '-'}] {'HEX' if macro.is_hex else 'ASCII'}: {macro.text}"
            item.setToolTip(tip)
            self.list.addItem(item)

    def _selected_name(self) -> str | None:
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item is not None else None

    # --- actions (split so tests can call without dialogs) ---------------- #
    def _save_current(self) -> None:
        name, ok = QInputDialog.getText(self, tr("macro.name_title"), tr("macro.name_prompt"))
        if not ok or not name.strip():
            return
        suggested = self._selected_group() or ""
        group, ok = QInputDialog.getText(
            self, tr("macro.name_title"), tr("macro.group_prompt"), text=suggested
        )
        if not ok:
            return
        self._save_named(name.strip(), group.strip())

    def _save_named(self, name: str, group: str = "") -> None:
        self._store.add(self._sender.snapshot(name=name, group=group))
        self._persist()
        self._reload_groups()
        self._reload_list()

    def _apply_selected(self) -> None:
        name = self._selected_name()
        if name is not None:
            self._apply_name(name)

    def _apply_name(self, name: str) -> bool:
        macro: Macro | None = self._store.get(name)
        if macro is None:
            return False
        self._sender.apply_macro(macro)
        return True

    def _delete_selected(self) -> None:
        name = self._selected_name()
        if name is None:
            return
        self._store.remove(name)
        self._persist()
        self._reload_groups()
        self._reload_list()

    def retranslate(self) -> None:
        self.setTitle(tr("group.macros"))
        self.btn_save.setText(tr("macro.save_current"))
        self.btn_apply.setText(tr("macro.apply"))
        self.btn_delete.setText(tr("macro.delete"))
        # The "(all)/(ungrouped)" entries are translated; refresh keeping selection.
        self._reload_groups()
