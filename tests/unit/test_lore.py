"""
Unit test per app/db/lore.py (DEPRECATED WI-8, rimozione gated P7).

Contratto:
  - add_lore_entry: title vuoto/lungo → ValueError; valid → id UUID
  - get_lore_entry: found/not found
  - list_lore_entries: filter category, all
  - update_lore_entry: partial update, not found → False, no fields → True
  - delete_lore_entry: found → True, not found → False
  - link_lore_to_arc + list_lore_for_arc: join query
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.lore import (
    add_lore_entry,
    delete_lore_entry,
    get_lore_entry,
    link_lore_to_arc,
    list_lore_entries,
    list_lore_for_arc,
    update_lore_entry,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _add(conn, title="Test Entry", category="other", content_text="content") -> str:
    return add_lore_entry(conn, title=title, category=category, content_text=content_text)


def _add_arc(conn, title="Arc") -> str:
    from app.db.arcs import create_arc
    return create_arc(conn, title=title)


# ── add_lore_entry ────────────────────────────────────────────────────────────

def test_add_lore_entry_with_empty_title(db_connection):
    conn = db_connection["conn"]
    with pytest.raises(ValueError):
        add_lore_entry(conn, title="", content_text="Some content")


def test_add_lore_entry_with_long_title(db_connection):
    conn = db_connection["conn"]
    with pytest.raises(ValueError):
        add_lore_entry(conn, title="a" * 256, content_text="Some content")


def test_add_lore_entry_returns_id(db_connection):
    conn = db_connection["conn"]
    entry_id = _add(conn, title="Leggende Oscure")
    assert entry_id and isinstance(entry_id, str)


def test_add_lore_entry_with_category(db_connection):
    conn = db_connection["conn"]
    entry_id = _add(conn, title="Mondo", category="world_setting")
    entry = get_lore_entry(conn, entry_id)
    assert entry["category"] == "world_setting"


# ── get_lore_entry ────────────────────────────────────────────────────────────

def test_get_lore_entry_found(db_connection):
    conn = db_connection["conn"]
    entry_id = _add(conn, title="Il Cristallo")
    entry = get_lore_entry(conn, entry_id)
    assert entry is not None
    assert entry["title"] == "Il Cristallo"


def test_get_lore_entry_not_found(db_connection):
    conn = db_connection["conn"]
    assert get_lore_entry(conn, "ghost-id") is None


# ── list_lore_entries ─────────────────────────────────────────────────────────

def test_list_lore_entries_empty(db_connection):
    conn = db_connection["conn"]
    assert list_lore_entries(conn) == []


def test_list_lore_entries_all(db_connection):
    conn = db_connection["conn"]
    _add(conn, title="E1")
    _add(conn, title="E2")
    entries = list_lore_entries(conn)
    assert len(entries) == 2


def test_list_lore_entries_filter_category(db_connection):
    conn = db_connection["conn"]
    _add(conn, title="Place1", category="places")
    _add(conn, title="World1", category="world_setting")
    places = list_lore_entries(conn, category="places")
    assert len(places) == 1
    assert places[0]["title"] == "Place1"


# ── update_lore_entry ─────────────────────────────────────────────────────────

def test_update_lore_entry_title(db_connection):
    conn = db_connection["conn"]
    entry_id = _add(conn, title="Vecchio")
    result = update_lore_entry(conn, entry_id, title="Nuovo")
    assert result is True
    assert get_lore_entry(conn, entry_id)["title"] == "Nuovo"


def test_update_lore_entry_content(db_connection):
    conn = db_connection["conn"]
    entry_id = _add(conn, title="E", content_text="old")
    update_lore_entry(conn, entry_id, content_text="new")
    assert get_lore_entry(conn, entry_id)["content_text"] == "new"


def test_update_lore_entry_not_found(db_connection):
    conn = db_connection["conn"]
    assert update_lore_entry(conn, "ghost", title="x") is False


def test_update_lore_entry_no_fields_returns_true(db_connection):
    conn = db_connection["conn"]
    entry_id = _add(conn, title="E")
    assert update_lore_entry(conn, entry_id) is True


# ── delete_lore_entry ─────────────────────────────────────────────────────────

def test_delete_lore_entry_found(db_connection):
    conn = db_connection["conn"]
    entry_id = _add(conn, title="Da Eliminare")
    assert delete_lore_entry(conn, entry_id) is True
    assert get_lore_entry(conn, entry_id) is None


def test_delete_lore_entry_not_found(db_connection):
    conn = db_connection["conn"]
    assert delete_lore_entry(conn, "ghost") is False


# ── link_lore_to_arc / list_lore_for_arc ──────────────────────────────────────

def test_list_lore_for_arc_empty(db_connection):
    conn = db_connection["conn"]
    arc_id = _add_arc(conn)
    assert list_lore_for_arc(conn, arc_id) == []


def test_link_lore_to_arc_and_list(db_connection):
    conn = db_connection["conn"]
    arc_id = _add_arc(conn, title="Arco Magico")
    entry_id = _add(conn, title="Incantesimo")
    link_lore_to_arc(conn, arc_id, entry_id)
    entries = list_lore_for_arc(conn, arc_id)
    assert len(entries) == 1
    assert entries[0]["id"] == entry_id


def test_list_lore_for_nonexistent_arc(db_connection):
    conn = db_connection["conn"]
    assert list_lore_for_arc(conn, "no-arc") == []
