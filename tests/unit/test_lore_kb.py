"""
Unit test per lore_kb.py — CRUD LoreStore + triggered_entries.

Contratto:
  - _validate_category: categoria valida → invariata; invalida → OTHER
  - _slugify: caratteri speciali → trattini, no trailing dashes
  - LoreEntry: category normalizzata in __post_init__, roundtrip to_dict/from_dict
  - LoreStore: load (file mancante, JSON corrotto), add/update/delete/get, list_by_category,
    triggered_entries (constant-first, keyword match, dedupe, max_entries)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.lore_kb import (
    LORE_CATEGORIES,
    OTHER,
    LoreEntry,
    LoreStore,
    _slugify,
    _validate_category,
)


# ── _validate_category ────────────────────────────────────────────────────────

def test_validate_category_valid():
    for cat in LORE_CATEGORIES:
        assert _validate_category(cat) == cat


def test_validate_category_invalid_falls_back():
    assert _validate_category("nonexistent_cat") == OTHER
    assert _validate_category("") == OTHER


# ── _slugify ──────────────────────────────────────────────────────────────────

def test_slugify_basic():
    assert _slugify("Hello World") == "hello-world"


def test_slugify_special_chars():
    # regex [^a-z0-9]+ collassa sequenze consecutive in un unico trattino
    result = _slugify("L'Éclipse!")
    assert "clipse" in result
    assert not result.startswith("-")
    assert not result.endswith("-")


def test_slugify_leading_trailing_dashes():
    result = _slugify("  !!! Title !!!")
    assert not result.startswith("-")
    assert not result.endswith("-")


def test_slugify_empty():
    assert _slugify("") == ""


# ── LoreEntry ─────────────────────────────────────────────────────────────────

def test_lore_entry_normalizes_invalid_category():
    e = LoreEntry(id="x", title="test", category="INVALID")
    assert e.category == OTHER


def test_lore_entry_roundtrip():
    e = LoreEntry(
        id="lore-1",
        title="Il Cristallo",
        category="mechanics_magic",
        keys=["cristallo", "gem"],
        content="Il cristallo è potente.",
        constant=True,
    )
    d = e.to_dict()
    e2 = LoreEntry.from_dict(d)
    assert e2.id == "lore-1"
    assert e2.title == "Il Cristallo"
    assert e2.category == "mechanics_magic"
    assert e2.keys == ["cristallo", "gem"]
    assert e2.content == "Il cristallo è potente."
    assert e2.constant is True


def test_lore_entry_from_dict_missing_fields():
    e = LoreEntry.from_dict({"id": "x", "title": "Minimal"})
    assert e.category == OTHER
    assert e.keys == []
    # from_dict usa data.get(k) → None per chiavi assenti (non il default del dataclass)
    assert not e.content


# ── LoreStore — persistenza ────────────────────────────────────────────────────

def _store(tmp_path) -> LoreStore:
    return LoreStore(path=tmp_path / "lore.json")


def test_store_empty_on_missing_file(tmp_path):
    store = _store(tmp_path)
    assert store.list_by_category() == []


def test_store_load_ignores_corrupt_json(tmp_path):
    p = tmp_path / "lore.json"
    p.write_text("NOT JSON {{{")
    store = LoreStore(path=p)
    assert store.list_by_category() == []


def test_store_add_entry_auto_id(tmp_path):
    store = _store(tmp_path)
    e = LoreEntry(id="", title="Il Bosco Oscuro", category="places", content="Un posto buio")
    added = store.add_entry(e)
    assert added.id == "il-bosco-oscuro"


def test_store_add_entry_persists(tmp_path):
    p = tmp_path / "lore.json"
    store = LoreStore(path=p)
    store.add_entry(LoreEntry(id="e1", title="Entry One", content="contenuto"))
    # Ricarica da file
    store2 = LoreStore(path=p)
    assert store2.get_entry("e1") is not None


def test_store_add_dedupes_on_same_id(tmp_path):
    store = _store(tmp_path)
    store.add_entry(LoreEntry(id="e1", title="A", content="old"))
    store.add_entry(LoreEntry(id="e1", title="A", content="new"))
    entries = store.list_by_category()
    assert len(entries) == 1
    assert entries[0].content == "new"


def test_store_add_generates_unique_id_on_collision(tmp_path):
    store = _store(tmp_path)
    store.add_entry(LoreEntry(id="test", title="Test"))
    e2 = store.add_entry(LoreEntry(id="", title="Test"))
    assert e2.id == "test-1"


def test_store_update_entry(tmp_path):
    store = _store(tmp_path)
    store.add_entry(LoreEntry(id="e1", title="Entry", content="old"))
    updated = store.update_entry("e1", content="new")
    assert updated is not None
    assert updated.content == "new"


def test_store_update_entry_not_found(tmp_path):
    store = _store(tmp_path)
    result = store.update_entry("does-not-exist", content="x")
    assert result is None


def test_store_update_category_validates(tmp_path):
    store = _store(tmp_path)
    store.add_entry(LoreEntry(id="e1", title="E", category="places"))
    updated = store.update_entry("e1", category="INVALID")
    assert updated.category == OTHER


def test_store_delete_entry(tmp_path):
    store = _store(tmp_path)
    store.add_entry(LoreEntry(id="e1", title="E"))
    assert store.delete_entry("e1") is True
    assert store.get_entry("e1") is None


def test_store_delete_entry_not_found(tmp_path):
    store = _store(tmp_path)
    assert store.delete_entry("ghost") is False


def test_store_get_entry_found(tmp_path):
    store = _store(tmp_path)
    store.add_entry(LoreEntry(id="e1", title="E"))
    assert store.get_entry("e1") is not None


def test_store_get_entry_not_found(tmp_path):
    store = _store(tmp_path)
    assert store.get_entry("nope") is None


# ── list_by_category ──────────────────────────────────────────────────────────

def test_list_by_category_filter(tmp_path):
    store = _store(tmp_path)
    store.add_entry(LoreEntry(id="p1", title="Luogo", category="places", insertion_order=1))
    store.add_entry(LoreEntry(id="m1", title="Magia", category="mechanics_magic", insertion_order=2))
    places = store.list_by_category("places")
    assert len(places) == 1
    assert places[0].id == "p1"


def test_list_by_category_sorted_by_insertion_order(tmp_path):
    store = _store(tmp_path)
    store.add_entry(LoreEntry(id="b", title="B", category="places", insertion_order=2))
    store.add_entry(LoreEntry(id="a", title="A", category="places", insertion_order=1))
    result = store.list_by_category("places")
    assert [e.id for e in result] == ["a", "b"]


def test_list_by_category_none_returns_all(tmp_path):
    store = _store(tmp_path)
    store.add_entry(LoreEntry(id="x1", title="X", category="places"))
    store.add_entry(LoreEntry(id="x2", title="Y", category="other"))
    all_entries = store.list_by_category()
    assert len(all_entries) == 2


# ── triggered_entries ─────────────────────────────────────────────────────────

def test_triggered_entries_empty(tmp_path):
    store = _store(tmp_path)
    assert store.triggered_entries("qualsiasi testo") == []


def test_triggered_entries_constant_always_included(tmp_path):
    store = _store(tmp_path)
    store.add_entry(LoreEntry(id="c1", title="Costante", constant=True, insertion_order=1))
    result = store.triggered_entries("testo senza chiavi")
    assert len(result) == 1
    assert result[0].id == "c1"


def test_triggered_entries_keyword_match(tmp_path):
    store = _store(tmp_path)
    store.add_entry(LoreEntry(id="k1", title="Drago", keys=["drago", "dragon"]))
    result = store.triggered_entries("c'era un drago nel bosco")
    assert any(e.id == "k1" for e in result)


def test_triggered_entries_case_insensitive(tmp_path):
    store = _store(tmp_path)
    store.add_entry(LoreEntry(id="k1", title="Drago", keys=["DRAGO"]))
    result = store.triggered_entries("il drago ruggì")
    assert any(e.id == "k1" for e in result)


def test_triggered_entries_no_match(tmp_path):
    store = _store(tmp_path)
    store.add_entry(LoreEntry(id="k1", title="Drago", keys=["drago"]))
    result = store.triggered_entries("nessun riferimento qui")
    assert result == []


def test_triggered_entries_constant_before_keyed(tmp_path):
    store = _store(tmp_path)
    store.add_entry(LoreEntry(id="c1", title="Costante", constant=True, insertion_order=2))
    store.add_entry(LoreEntry(id="k1", title="Keyed", keys=["bosco"], insertion_order=1))
    result = store.triggered_entries("nel bosco oscuro")
    # constant viene prima anche se insertion_order maggiore
    assert result[0].id == "c1"


def test_triggered_entries_no_duplicate(tmp_path):
    store = _store(tmp_path)
    store.add_entry(LoreEntry(id="k1", title="E", keys=["parola", "parola"], constant=False))
    result = store.triggered_entries("la parola magica")
    ids = [e.id for e in result]
    assert ids.count("k1") == 1


def test_triggered_entries_max_entries(tmp_path):
    store = _store(tmp_path)
    for i in range(10):
        store.add_entry(LoreEntry(id=f"c{i}", title=f"C{i}", constant=True, insertion_order=i))
    result = store.triggered_entries("x", max_entries=3)
    assert len(result) == 3


# ── coverage gaps: default path, non-list JSON, unknown field ─────────────────

def test_default_store_path_is_json():
    from app.calliope_shell.lore_kb import _default_store_path
    p = _default_store_path()
    assert p.name == "lore_kb.json"
    assert "data" in str(p)


def test_store_init_none_path_uses_default(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.calliope_shell.lore_kb._default_store_path",
        lambda: tmp_path / "default_lore.json",
    )
    store = LoreStore(path=None)
    assert store.path == tmp_path / "default_lore.json"


def test_store_load_non_list_json_resets(tmp_path):
    import json as _json
    p = tmp_path / "lore.json"
    p.write_text(_json.dumps({"key": "value"}))
    store = LoreStore(path=p)
    assert store.list_by_category() == []


def test_update_entry_ignores_unknown_field(tmp_path):
    store = _store(tmp_path)
    store.add_entry(LoreEntry(id="e1", title="E", content="old"))
    updated = store.update_entry("e1", content="new", nonexistent_field="ignored")
    assert updated is not None
    assert updated.content == "new"


def test_lore_entry_to_dict_includes_extensions_when_set():
    e = LoreEntry(id="x", title="T", extensions={"color": "red"})
    d = e.to_dict()
    assert d["extensions"] == {"color": "red"}


def test_save_finally_cleans_tmp_on_replace_failure(tmp_path):
    """Lines 174-175: finally cleanup eseguito quando replace fallisce."""
    import pathlib
    from unittest.mock import patch
    import pytest

    store = _store(tmp_path)
    store.add_entry(LoreEntry(id="t1", title="Test", content="ok"))

    with patch.object(pathlib.Path, "replace", side_effect=OSError("disk full")):
        with pytest.raises(OSError):
            store.save()

    tmp_file = store.path.with_suffix(".tmp")
    assert not tmp_file.exists()


def test_save_finally_unlink_oserror_silenced(tmp_path):
    """Lines 176-177: OSError in unlink durante cleanup è silenziata."""
    import pathlib
    from unittest.mock import patch
    import pytest

    store = _store(tmp_path)
    store.add_entry(LoreEntry(id="t1", title="Test", content="ok"))

    with patch.object(pathlib.Path, "replace", side_effect=OSError("disk full")), \
         patch.object(pathlib.Path, "unlink", side_effect=OSError("permission denied")):
        with pytest.raises(OSError):
            store.save()
    # OSError da unlink è silenziosamente ignorata — nessuna eccezione qui
