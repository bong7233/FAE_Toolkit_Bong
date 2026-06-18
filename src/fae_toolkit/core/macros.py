"""Persistent, named send-frames ("macros") for the comm tester.

Industrial devices from different makers use different frame layouts, so the
single most-used feature of tools like Docklight / Hercules is the ability to
save the exact bytes for a device (grouped per maker) and recall them with one
click.  The store is deliberately Qt-free so it can be unit-tested and reused
headlessly; the GUI in :mod:`fae_toolkit.ui.comm.macros_panel` is a thin shell
around it.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path


def default_store_path() -> Path:
    """Per-user JSON file where macros are persisted."""
    return Path.home() / ".fae_toolkit" / "macros.json"


@dataclass
class Macro:
    """A reusable send-frame: the literal entry plus the send options.

    ``text`` is interpreted as HEX or ASCII according to ``is_hex`` (matching
    the frame sender), so applying a macro restores exactly what the user typed.
    ``group`` is a free-form label, typically a device maker or protocol family.
    """

    name: str
    text: str
    is_hex: bool = True
    append_crc: bool = False
    append_newline: bool = False
    group: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> Macro:
        return cls(
            name=str(d.get("name", "")),
            text=str(d.get("text", "")),
            is_hex=bool(d.get("is_hex", True)),
            append_crc=bool(d.get("append_crc", False)),
            append_newline=bool(d.get("append_newline", False)),
            group=str(d.get("group", "")),
        )


class MacroStore:
    """An ordered collection of uniquely-named macros with JSON persistence."""

    def __init__(self, macros: list[Macro] | None = None) -> None:
        self._macros: list[Macro] = list(macros or [])

    def __len__(self) -> int:
        return len(self._macros)

    def __iter__(self) -> Iterator[Macro]:
        return iter(self._macros)

    @property
    def macros(self) -> list[Macro]:
        return list(self._macros)

    def names(self) -> list[str]:
        return [m.name for m in self._macros]

    def groups(self) -> list[str]:
        """Distinct group labels in first-seen order."""
        seen: list[str] = []
        for m in self._macros:
            if m.group not in seen:
                seen.append(m.group)
        return seen

    def get(self, name: str) -> Macro | None:
        return next((m for m in self._macros if m.name == name), None)

    def filter(self, group: str | None) -> list[Macro]:
        """Macros in *group*; ``None`` returns all of them."""
        if group is None:
            return list(self._macros)
        return [m for m in self._macros if m.group == group]

    def add(self, macro: Macro) -> None:
        """Add a macro, replacing any existing one with the same name."""
        self.remove(macro.name)
        self._macros.append(macro)

    def remove(self, name: str) -> bool:
        for i, m in enumerate(self._macros):
            if m.name == name:
                del self._macros[i]
                return True
        return False

    def to_json(self) -> str:
        return json.dumps([asdict(m) for m in self._macros], indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> MacroStore:
        raw = json.loads(text) if text.strip() else []
        return cls([Macro.from_dict(d) for d in raw])

    def save(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str) -> MacroStore:
        """Load a store, returning an empty one for a missing/corrupt file."""
        path = Path(path)
        if not path.exists():
            return cls()
        try:
            return cls.from_json(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, ValueError):
            return cls()


def default_macros() -> list[Macro]:
    """A few illustrative macros seeded on first run."""
    return [
        Macro(
            name="Modbus: Read 10 holding regs",
            text="01 03 00 00 00 0A",
            is_hex=True,
            append_crc=True,
            group="Modbus",
        ),
        Macro(
            name="Modbus: Read 8 coils",
            text="01 01 00 00 00 08",
            is_hex=True,
            append_crc=True,
            group="Modbus",
        ),
        Macro(
            name="Modbus: Write reg #0 = 1",
            text="01 06 00 00 00 01",
            is_hex=True,
            append_crc=True,
            group="Modbus",
        ),
        Macro(
            name="ASCII: AT ping",
            text="AT",
            is_hex=False,
            append_newline=True,
            group="ASCII",
        ),
    ]
