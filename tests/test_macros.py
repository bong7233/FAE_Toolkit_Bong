"""Tests for the Qt-free saved-frame (macro) store."""

from fae_toolkit.core.macros import Macro, MacroStore, default_macros


def test_add_get_and_names():
    store = MacroStore()
    store.add(Macro("read", "01 03 00 00 00 0A", append_crc=True, group="Modbus"))
    store.add(Macro("ping", "AT", is_hex=False, append_newline=True, group="ASCII"))
    assert store.names() == ["read", "ping"]
    m = store.get("read")
    assert m is not None and m.append_crc and m.group == "Modbus"
    assert store.get("missing") is None
    assert len(store) == 2


def test_add_replaces_same_name():
    store = MacroStore()
    store.add(Macro("x", "00"))
    store.add(Macro("x", "FF"))
    assert len(store) == 1
    assert store.get("x").text == "FF"


def test_remove():
    store = MacroStore([Macro("a", "00"), Macro("b", "11")])
    assert store.remove("a") is True
    assert store.remove("a") is False
    assert store.names() == ["b"]


def test_groups_and_filter():
    store = MacroStore(
        [
            Macro("a", "00", group="LG"),
            Macro("b", "11", group="Samsung"),
            Macro("c", "22", group="LG"),
        ]
    )
    assert store.groups() == ["LG", "Samsung"]
    assert [m.name for m in store.filter("LG")] == ["a", "c"]
    assert [m.name for m in store.filter(None)] == ["a", "b", "c"]


def test_json_roundtrip_preserves_unicode():
    store = MacroStore([Macro("배터리 읽기", "01 03", group="제조사A")])
    restored = MacroStore.from_json(store.to_json())
    m = restored.get("배터리 읽기")
    assert m is not None and m.group == "제조사A"


def test_save_and_load_file(tmp_path):
    path = tmp_path / "sub" / "macros.json"
    store = MacroStore(default_macros())
    store.save(path)  # creates parent dir
    assert path.exists()
    reloaded = MacroStore.load(path)
    assert reloaded.names() == store.names()


def test_load_missing_returns_empty(tmp_path):
    assert len(MacroStore.load(tmp_path / "nope.json")) == 0


def test_load_corrupt_returns_empty(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    assert len(MacroStore.load(path)) == 0


def test_default_macros_are_valid():
    macros = default_macros()
    assert macros
    assert all(m.name and m.text for m in macros)
