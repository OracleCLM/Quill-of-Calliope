import pytest
from app.calliope_shell.lore_kb import (
    LoreEntry,
    LoreStore,
    LORE_CATEGORIES,
    WORLD_SETTING,
    PLACES,
    CHARACTERS_EVENTS,
    MECHANICS_MAGIC,
    OTHER,
)


@pytest.mark.unit
def test_categories():
    assert len(LORE_CATEGORIES) == 5
    for const in (WORLD_SETTING, PLACES, CHARACTERS_EVENTS, MECHANICS_MAGIC, OTHER):
        assert const in LORE_CATEGORIES


@pytest.mark.unit
def test_entry_invalid_category_falls_to_other():
    entry = LoreEntry(id="x", title="t", category="bogus")
    assert entry.category == OTHER


@pytest.mark.unit
def test_entry_roundtrip_extensions():
    data = {"id": "a", "title": "A", "extensions": {"k": "v"}}
    entry = LoreEntry.from_dict(data)
    out = entry.to_dict()
    assert "extensions" in out
    assert out["extensions"]["k"] == "v"


@pytest.mark.unit
def test_crud(tmp_path):
    store_path = str(tmp_path / "kb.json")
    store = LoreStore(store_path)

    # Aggiunta (id generato automaticamente)
    entry = LoreEntry(id="", title="Capital City", category=PLACES, content="c")
    added = store.add_entry(entry)
    assert added.id  # id non vuoto
    entry_id = added.id

    # Recupero
    fetched = store.get_entry(entry_id)
    assert fetched is not None
    assert fetched.title == "Capital City"

    # Aggiornamento
    updated = store.update_entry(entry_id, content="c2")
    assert updated is not None
    assert updated.content == "c2"

    # Lista per categoria
    lst = store.list_by_category(PLACES)
    assert len(lst) == 1
    assert lst[0].id == entry_id

    # Cancellazione
    assert store.delete_entry(entry_id) is True
    assert store.get_entry(entry_id) is None


@pytest.mark.unit
def test_persistence(tmp_path):
    store_path = str(tmp_path / "kb.json")
    store = LoreStore(store_path)
    store.add_entry(LoreEntry(id="e1", title="X", category=WORLD_SETTING))

    # Ricarica da disco
    store2 = LoreStore(store_path)
    assert len(store2.list_by_category()) >= 1
    # Verifica che l'entry aggiunta sia presente
    entry = store2.get_entry("e1")
    assert entry is not None
    assert entry.title == "X"
    assert entry.category == WORLD_SETTING


@pytest.mark.unit
def test_triggered_constant_first(tmp_path):
    store = LoreStore(str(tmp_path / "kb.json"))

    # Entry costante
    const_entry = LoreEntry(
        id="c1",
        title="Const",
        content="always",
        constant=True,
        insertion_order=10,
    )
    store.add_entry(const_entry)

    # Entry con keyword
    keyed_entry = LoreEntry(
        id="k1",
        title="Keyed",
        keys=["dragon"],
        content="kw",
        insertion_order=20,
    )
    store.add_entry(keyed_entry)

    results = store.triggered_entries("a dragon appears")
    ids = [e.id for e in results]

    # Entrambe devono comparire
    assert "c1" in ids
    assert "k1" in ids

    # L'entry costante deve precedere quella con keyword
    assert ids.index("c1") < ids.index("k1")


@pytest.mark.unit
def test_missing_file_empty(tmp_path):
    # Il file non esiste
    store = LoreStore(str(tmp_path / "nonexistent.json"))
    assert store.list_by_category() == []
