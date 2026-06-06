"""Acceptance contract for app/db/lore.py — the Lore knowledge-base CRUD layer.

Pre-written by the orchestrator (operator-wanted: editable Lore KB, 5 categories) so a
cost-zero worker implements app/db/lore.py to satisfy THESE assertions — the contract is
authored here, not by the worker, so a green run means the real behaviour is met (no toy).

Raw sqlite3 only (matches app/db/reactions.py + app/db/__init__.py). NO sqlalchemy.

Required app/db/lore.py public API (raw sqlite3, conn-first, ids via app.db.new_id):
  add_lore_entry(conn, *, title, category="other", content_text=None, created_by="operator") -> str
  get_lore_entry(conn, entry_id) -> dict | None
  list_lore_entries(conn, category=None) -> list[dict]
  update_lore_entry(conn, entry_id, *, title=None, content_text=None, category=None) -> bool
  delete_lore_entry(conn, entry_id) -> bool
  link_lore_to_arc(conn, arc_id, entry_id) -> None
  list_lore_for_arc(conn, arc_id) -> list[dict]
"""
import sqlite3
import tempfile
from pathlib import Path

import pytest

import app.db as db_mod
from app.db.lore import (
    add_lore_entry,
    get_lore_entry,
    list_lore_entries,
    update_lore_entry,
    delete_lore_entry,
    link_lore_to_arc,
    list_lore_for_arc,
)

CATEGORIES = ["world_setting", "places", "characters_events", "mechanics_magic", "other"]


@pytest.fixture
def db_connection():
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        db_path = Path(tf.name)
    conn = sqlite3.connect(str(db_path))
    try:
        db_mod.init_schema(conn)
        # an arc to exercise the arc_lore association (arcs.title is NOT NULL)
        arc_id = db_mod.new_id()
        conn.execute("INSERT INTO arcs (id, title) VALUES (?, ?)", (arc_id, "Arc 1"))
        conn.commit()
        yield {"conn": conn, "arc_id": arc_id}
    finally:
        conn.close()
        db_path.unlink(missing_ok=True)


def test_add_and_get(db_connection):
    conn = db_connection["conn"]
    eid = add_lore_entry(conn, title="The Old Kingdom", category="world_setting",
                         content_text="Lore body")
    assert isinstance(eid, str) and eid
    row = get_lore_entry(conn, eid)
    assert row is not None
    assert row["title"] == "The Old Kingdom"
    assert row["category"] == "world_setting"
    assert row["content_text"] == "Lore body"


def test_default_category_is_other(db_connection):
    conn = db_connection["conn"]
    eid = add_lore_entry(conn, title="Untagged note")
    assert get_lore_entry(conn, eid)["category"] == "other"


def test_all_five_categories_accepted(db_connection):
    conn = db_connection["conn"]
    for cat in CATEGORIES:
        eid = add_lore_entry(conn, title=f"t-{cat}", category=cat)
        assert get_lore_entry(conn, eid)["category"] == cat


def test_invalid_category_rejected(db_connection):
    conn = db_connection["conn"]
    with pytest.raises(sqlite3.IntegrityError):
        add_lore_entry(conn, title="bad", category="not_a_category")


def test_list_all_and_by_category(db_connection):
    conn = db_connection["conn"]
    add_lore_entry(conn, title="a", category="places")
    add_lore_entry(conn, title="b", category="places")
    add_lore_entry(conn, title="c", category="mechanics_magic")
    assert len(list_lore_entries(conn)) == 3
    places = list_lore_entries(conn, category="places")
    assert len(places) == 2
    assert {r["title"] for r in places} == {"a", "b"}


def test_update(db_connection):
    conn = db_connection["conn"]
    eid = add_lore_entry(conn, title="old", category="other")
    assert update_lore_entry(conn, eid, title="new", content_text="body", category="places") is True
    row = get_lore_entry(conn, eid)
    assert row["title"] == "new"
    assert row["content_text"] == "body"
    assert row["category"] == "places"


def test_delete(db_connection):
    conn = db_connection["conn"]
    eid = add_lore_entry(conn, title="temp")
    assert delete_lore_entry(conn, eid) is True
    assert get_lore_entry(conn, eid) is None


def test_link_and_list_for_arc(db_connection):
    conn = db_connection["conn"]
    arc_id = db_connection["arc_id"]
    e1 = add_lore_entry(conn, title="linked-1", category="places")
    e2 = add_lore_entry(conn, title="linked-2", category="other")
    add_lore_entry(conn, title="unlinked", category="other")
    link_lore_to_arc(conn, arc_id, e1)
    link_lore_to_arc(conn, arc_id, e2)
    rows = list_lore_for_arc(conn, arc_id)
    assert {r["title"] for r in rows} == {"linked-1", "linked-2"}
