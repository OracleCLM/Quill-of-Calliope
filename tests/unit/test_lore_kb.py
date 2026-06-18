"""GAP-39: test unitari per lore_kb — LoreEntry, LoreStore CRUD, triggered_entries."""

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


def _store(tmp_path) -> LoreStore:
    return LoreStore(path=tmp_path / "lore_kb.json")


def _entry(title="Castello", keys=None, content="", constant=False, category=OTHER, insertion_order=100):
    return LoreEntry(id="", title=title, keys=keys or [], content=content,
                     constant=constant, category=category, insertion_order=insertion_order)


# ── _validate_category ────────────────────────────────────────────────────────


def test_validate_category_known():
    for cat in LORE_CATEGORIES:
        assert _validate_category(cat) == cat


def test_validate_category_unknown_returns_other():
    assert _validate_category("sconosciuta") == OTHER


# ── _slugify ──────────────────────────────────────────────────────────────────


def test_slugify_lowercase_dash():
    assert _slugify("Il Castello Oscuro") == "il-castello-oscuro"


def test_slugify_empty_empty():
    assert _slugify("") == ""


# ── LoreEntry serialization ───────────────────────────────────────────────────


def test_to_dict_has_required_keys():
    e = LoreEntry(id="x", title="Test")
    d = e.to_dict()
    for key in ("id", "title", "category", "keys", "content", "insertion_order", "scope", "constant"):
        assert key in d


def test_from_dict_round_trip():
    e = LoreEntry(id="e1", title="Midgard", category="places", keys=["midgard"], content="Reame nordico",
                  insertion_order=5, scope="global", constant=True, extensions={"foo": "bar"})
    restored = LoreEntry.from_dict(e.to_dict())
    assert restored.id == "e1"
    assert restored.title == "Midgard"
    assert restored.keys == ["midgard"]
    assert restored.constant is True


def test_unknown_category_normalized_on_init():
    e = LoreEntry(id="z", title="X", category="fantasy")
    assert e.category == OTHER


# ── LoreStore — file lifecycle ────────────────────────────────────────────────


def test_store_loads_empty_when_no_file(tmp_path):
    store = _store(tmp_path)
    assert store.list_by_category() == []


def test_store_persists_to_json(tmp_path):
    store = _store(tmp_path)
    store.add_entry(_entry("Foresta"))
    assert (tmp_path / "lore_kb.json").exists()


def test_store_reloads_from_json(tmp_path):
    store = _store(tmp_path)
    store.add_entry(_entry("Foresta"))
    store2 = _store(tmp_path)
    assert len(store2.list_by_category()) == 1
    assert store2.list_by_category()[0].title == "Foresta"


def test_store_loads_gracefully_on_invalid_json(tmp_path):
    path = tmp_path / "lore_kb.json"
    path.write_text("{not-valid-json}", encoding="utf-8")
    store = LoreStore(path=path)
    assert store.list_by_category() == []


# ── LoreStore — add_entry ─────────────────────────────────────────────────────


def test_add_entry_assigns_id(tmp_path):
    store = _store(tmp_path)
    added = store.add_entry(_entry("Castello"))
    assert added.id != ""


def test_add_entry_slugifies_title(tmp_path):
    store = _store(tmp_path)
    added = store.add_entry(_entry("Il Castello Oscuro"))
    assert "castello" in added.id


def test_add_entry_unique_id_collision(tmp_path):
    store = _store(tmp_path)
    a = store.add_entry(_entry("Torre"))
    b = store.add_entry(_entry("Torre"))
    assert a.id != b.id


# ── LoreStore — get / update / delete ────────────────────────────────────────


def test_get_entry_returns_none_for_missing(tmp_path):
    store = _store(tmp_path)
    assert store.get_entry("inesistente") is None


def test_get_entry_returns_correct(tmp_path):
    store = _store(tmp_path)
    added = store.add_entry(_entry("Lago"))
    assert store.get_entry(added.id).title == "Lago"


def test_update_entry_changes_field(tmp_path):
    store = _store(tmp_path)
    added = store.add_entry(_entry("Lago"))
    updated = store.update_entry(added.id, content="Lago incantato")
    assert updated.content == "Lago incantato"


def test_update_entry_invalid_category_normalized(tmp_path):
    store = _store(tmp_path)
    added = store.add_entry(_entry("X"))
    updated = store.update_entry(added.id, category="garbage")
    assert updated.category == OTHER


def test_update_entry_none_for_missing(tmp_path):
    store = _store(tmp_path)
    assert store.update_entry("xxx", content="test") is None


def test_delete_entry_returns_true(tmp_path):
    store = _store(tmp_path)
    added = store.add_entry(_entry("Bosco"))
    assert store.delete_entry(added.id) is True


def test_delete_entry_removes_it(tmp_path):
    store = _store(tmp_path)
    added = store.add_entry(_entry("Bosco"))
    store.delete_entry(added.id)
    assert store.get_entry(added.id) is None


def test_delete_entry_false_for_missing(tmp_path):
    store = _store(tmp_path)
    assert store.delete_entry("nonexistent") is False


# ── LoreStore — list_by_category ─────────────────────────────────────────────


def test_list_by_category_all(tmp_path):
    store = _store(tmp_path)
    store.add_entry(_entry("A", category="places"))
    store.add_entry(_entry("B", category="other"))
    assert len(store.list_by_category()) == 2


def test_list_by_category_filtered(tmp_path):
    store = _store(tmp_path)
    store.add_entry(_entry("A", category="places"))
    store.add_entry(_entry("B", category="other"))
    result = store.list_by_category("places")
    assert len(result) == 1 and result[0].title == "A"


def test_list_by_category_sorted_by_insertion_order(tmp_path):
    store = _store(tmp_path)
    e1 = LoreEntry(id="", title="Z", insertion_order=10)
    e2 = LoreEntry(id="", title="A", insertion_order=5)
    store.add_entry(e1)
    store.add_entry(e2)
    result = store.list_by_category()
    assert result[0].insertion_order <= result[1].insertion_order


# ── LoreStore — triggered_entries ────────────────────────────────────────────


def test_triggered_entries_constant_always_included(tmp_path):
    store = _store(tmp_path)
    const = LoreEntry(id="", title="Legge", constant=True, keys=[])
    store.add_entry(const)
    hits = store.triggered_entries("qualsiasi testo senza chiavi")
    assert any(e.constant for e in hits)


def test_triggered_entries_key_match(tmp_path):
    store = _store(tmp_path)
    e = LoreEntry(id="", title="Drago", keys=["drago"])
    store.add_entry(e)
    hits = store.triggered_entries("Il drago attaccò il villaggio")
    ids = [h.id for h in hits]
    assert e.id in ids or any(h.title == "Drago" for h in hits)


def test_triggered_entries_no_match_returns_only_constants(tmp_path):
    store = _store(tmp_path)
    e = LoreEntry(id="", title="Elfo", keys=["elfo"])
    store.add_entry(e)
    hits = store.triggered_entries("Aurora arrivò al castello")
    assert all(h.title != "Elfo" for h in hits)


def test_triggered_entries_deduped(tmp_path):
    store = _store(tmp_path)
    e = LoreEntry(id="", title="Lupo", keys=["lupo", "lupi"])
    store.add_entry(e)
    hits = store.triggered_entries("il lupo e i lupi")
    assert len([h for h in hits if h.title == "Lupo"]) == 1


def test_triggered_entries_max_respected(tmp_path):
    store = _store(tmp_path)
    for i in range(30):
        store.add_entry(LoreEntry(id="", title=f"E{i}", constant=True))
    hits = store.triggered_entries("testo", max_entries=5)
    assert len(hits) <= 5
