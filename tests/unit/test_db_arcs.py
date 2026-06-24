"""
Unit test per app/db/arcs.py — CRUD archi narrativi.

Usa la fixture db_connection (SQLite in-memory con schema completo).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.arcs import (
    create_arc,
    delete_arc,
    get_arc,
    list_arcs,
    list_scenes_for_arc,
    update_arc,
)
from tests.unit.conftest import add_scene


# ── create_arc ────────────────────────────────────────────────────────────────

def test_create_arc_returns_id(db_connection):
    conn = db_connection["conn"]
    arc_id = create_arc(conn, title="Il Primo Arco")
    assert arc_id and isinstance(arc_id, str)


def test_create_arc_empty_title_raises(db_connection):
    conn = db_connection["conn"]
    with pytest.raises(ValueError, match="title is required"):
        create_arc(conn, title="")


def test_create_arc_with_description(db_connection):
    conn = db_connection["conn"]
    arc_id = create_arc(conn, title="Arco", description="Descrizione lunga")
    arc = get_arc(conn, arc_id)
    assert arc["description"] == "Descrizione lunga"


# ── list_arcs ─────────────────────────────────────────────────────────────────

def test_list_arcs_empty(db_connection):
    conn = db_connection["conn"]
    assert list_arcs(conn) == []


def test_list_arcs_returns_all(db_connection):
    conn = db_connection["conn"]
    create_arc(conn, title="A1")
    create_arc(conn, title="A2")
    arcs = list_arcs(conn)
    assert len(arcs) == 2
    titles = {a["title"] for a in arcs}
    assert titles == {"A1", "A2"}


# ── get_arc ───────────────────────────────────────────────────────────────────

def test_get_arc_found(db_connection):
    conn = db_connection["conn"]
    arc_id = create_arc(conn, title="Trovato")
    arc = get_arc(conn, arc_id)
    assert arc is not None
    assert arc["title"] == "Trovato"


def test_get_arc_not_found(db_connection):
    conn = db_connection["conn"]
    assert get_arc(conn, "does-not-exist") is None


# ── delete_arc ────────────────────────────────────────────────────────────────

def test_delete_arc_returns_true(db_connection):
    conn = db_connection["conn"]
    arc_id = create_arc(conn, title="Da Eliminare")
    assert delete_arc(conn, arc_id) is True
    assert get_arc(conn, arc_id) is None


def test_delete_arc_not_found_returns_false(db_connection):
    conn = db_connection["conn"]
    assert delete_arc(conn, "ghost-arc") is False


# ── list_scenes_for_arc ────────────────────────────────────────────────────────

def test_list_scenes_for_arc_empty(db_connection):
    conn = db_connection["conn"]
    arc_id = create_arc(conn, title="Arco Vuoto")
    assert list_scenes_for_arc(conn, arc_id) == []


def test_list_scenes_for_arc_returns_scenes(db_connection):
    conn = db_connection["conn"]
    arc_id = create_arc(conn, title="Arco con Scene")
    # Inserisce una scena con arc_id
    scene_id = add_scene(conn, title="Scena1")
    conn.execute("UPDATE scenes SET arc_id = ? WHERE id = ?", (arc_id, scene_id))
    conn.commit()
    scenes = list_scenes_for_arc(conn, arc_id)
    assert len(scenes) == 1
    assert scenes[0]["id"] == scene_id


def test_list_scenes_for_arc_nonexistent_arc(db_connection):
    conn = db_connection["conn"]
    assert list_scenes_for_arc(conn, "nonexistent") == []


# ── update_arc ────────────────────────────────────────────────────────────────

def test_update_arc_title(db_connection):
    conn = db_connection["conn"]
    arc_id = create_arc(conn, title="Vecchio Titolo")
    result = update_arc(conn, arc_id, title="Nuovo Titolo")
    assert result is True
    assert get_arc(conn, arc_id)["title"] == "Nuovo Titolo"


def test_update_arc_description(db_connection):
    conn = db_connection["conn"]
    arc_id = create_arc(conn, title="Arco")
    result = update_arc(conn, arc_id, description="Nuova descrizione")
    assert result is True
    assert get_arc(conn, arc_id)["description"] == "Nuova descrizione"


def test_update_arc_not_found(db_connection):
    conn = db_connection["conn"]
    assert update_arc(conn, "ghost", title="x") is False


def test_update_arc_no_valid_fields(db_connection):
    conn = db_connection["conn"]
    arc_id = create_arc(conn, title="Arco")
    result = update_arc(conn, arc_id, unknown_field="x")
    assert result is False


def test_update_arc_ignores_unknown_fields(db_connection):
    conn = db_connection["conn"]
    arc_id = create_arc(conn, title="Arco")
    result = update_arc(conn, arc_id, title="Aggiornato", extra_field="ignored")
    assert result is True
    arc = get_arc(conn, arc_id)
    assert arc["title"] == "Aggiornato"
