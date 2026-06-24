"""
Unit test E1+E2 — lore_retrieval_for_scene + sheet_retrieval_for_scene.

Gate: pytest puro, no LLM, no Flask, no network.
"""
import pytest

from app.calliope_shell.lore_kb import LoreEntry, LoreStore
from app.calliope_shell.scene_context import (
    lore_retrieval_for_scene,
    sheet_retrieval_for_scene,
)
from app.db import get_db, init_schema
from app.db.characters import (
    add_character,
    add_character_to_scene,
)


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def lore_store():
    store = LoreStore.__new__(LoreStore)
    store._entries = []
    store._next_order = 0
    store._path = None

    def _add(title, keys=(), content="", constant=False):
        entry = LoreEntry(
            id=title.lower().replace(" ", "_"),
            title=title,
            keys=list(keys),
            content=content,
            constant=constant,
            insertion_order=store._next_order,
        )
        store._entries.append(entry)
        store._next_order += 1

    _add("Drago di Frostheim", keys=["drago", "frostheim"], content="Il drago abita il nord.", constant=False)
    _add("Magia antica", keys=["magia", "incantesimo"], content="Sistema magico del mondo.", constant=False)
    _add("Regole mondo", keys=[], content="Entry sempre attiva.", constant=True)
    return store


@pytest.fixture()
def db_with_roster(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)

    conn.execute("INSERT INTO scenes (id, title) VALUES ('sc1', 'Test Scene')")
    conn.commit()

    add_character(conn, name="Aurora", kind="player")
    add_character(conn, name="Sable", kind="npc")
    conn.commit()

    # Recupera gli id generati
    aurora_id = conn.execute("SELECT id FROM characters WHERE name='Aurora'").fetchone()[0]
    sable_id = conn.execute("SELECT id FROM characters WHERE name='Sable'").fetchone()[0]

    add_character_to_scene(conn, scene_id="sc1", character_id=aurora_id, role="narrator")
    add_character_to_scene(conn, scene_id="sc1", character_id=sable_id, role="npc")

    # Schede per Aurora (2 blocchi)
    for i, text in enumerate(["Aurora è una guerriera del gelo.", "Ha un passato oscuro."]):
        conn.execute(
            "INSERT INTO character_sheets (id, character_name, character_id, content, position_order)"
            " VALUES (?, ?, ?, ?, ?)",
            (f"sh_aurora_{i}", "Aurora", aurora_id, text, i),
        )
    # Sable ha 0 schede

    conn.commit()
    yield conn
    conn.close()


# ── E1 — lore_retrieval_for_scene ────────────────────────────────────────────

def test_e1_constant_entry_always_returned(lore_store):
    result = lore_retrieval_for_scene("testo senza keyword", lore_store)
    titles = [e.title for e in result]
    assert "Regole mondo" in titles


def test_e1_key_match_returns_relevant_entry(lore_store):
    result = lore_retrieval_for_scene("Il drago attacca il villaggio", lore_store)
    titles = [e.title for e in result]
    assert "Drago di Frostheim" in titles


def test_e1_non_matching_entry_excluded(lore_store):
    result = lore_retrieval_for_scene("una normale giornata", lore_store)
    titles = [e.title for e in result]
    assert "Magia antica" not in titles


def test_e1_empty_text_returns_only_constants(lore_store):
    result = lore_retrieval_for_scene("", lore_store)
    assert all(e.constant for e in result)
    assert len(result) == 1  # solo "Regole mondo"


# ── E2 — sheet_retrieval_for_scene ───────────────────────────────────────────

def test_e2_returns_roster_with_sheets(db_with_roster):
    result = sheet_retrieval_for_scene(db_with_roster, "sc1")
    names = {r["name"] for r in result}
    assert "Aurora" in names
    assert "Sable" in names


def test_e2_aurora_has_two_sheets(db_with_roster):
    result = sheet_retrieval_for_scene(db_with_roster, "sc1")
    aurora = next(r for r in result if r["name"] == "Aurora")
    assert len(aurora["sheets"]) == 2
    assert aurora["sheets"][0] == "Aurora è una guerriera del gelo."


def test_e2_sable_has_no_sheets(db_with_roster):
    result = sheet_retrieval_for_scene(db_with_roster, "sc1")
    sable = next(r for r in result if r["name"] == "Sable")
    assert sable["sheets"] == []


def test_e2_role_preserved(db_with_roster):
    result = sheet_retrieval_for_scene(db_with_roster, "sc1")
    aurora = next(r for r in result if r["name"] == "Aurora")
    assert aurora["role"] == "narrator"


def test_e2_empty_scene_returns_empty(db_with_roster):
    db_with_roster.execute("INSERT INTO scenes (id, title) VALUES ('sc_empty', 'Empty')")
    db_with_roster.commit()
    result = sheet_retrieval_for_scene(db_with_roster, "sc_empty")
    assert result == []
