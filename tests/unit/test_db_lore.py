"""GAP-41: test unitari per app/db/lore — add/get/list/update/delete/link_arc."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from app.db import get_db, init_schema, new_id
from app.db.lore import (
    add_lore_entry,
    delete_lore_entry,
    get_lore_entry,
    link_lore_to_arc,
    list_lore_entries,
    list_lore_for_arc,
    update_lore_entry,
)


@pytest.fixture
def conn(tmp_path):
    c = get_db(str(tmp_path / "test.db"))
    init_schema(c)
    yield c
    c.close()


def _add(conn, title="Midgard", category="world_setting", content="testo"):
    return add_lore_entry(conn, title=title, category=category, content_text=content)


# ── add_lore_entry ───────────────────────────────────────────────────────────


def test_add_returns_id(conn):
    eid = _add(conn)
    assert isinstance(eid, str) and eid


def test_add_empty_title_raises(conn):
    with pytest.raises(ValueError):
        add_lore_entry(conn, title="", content_text="testo")


def test_add_long_title_raises(conn):
    with pytest.raises(ValueError):
        add_lore_entry(conn, title="x" * 256, content_text="testo")


def test_add_persists(conn):
    eid = _add(conn, title="Castello")
    row = get_lore_entry(conn, eid)
    assert row is not None
    assert row["title"] == "Castello"


def test_add_content_stored(conn):
    eid = _add(conn, content="Contenuto magico")
    row = get_lore_entry(conn, eid)
    assert row["content_text"] == "Contenuto magico"


def test_add_category_stored(conn):
    eid = _add(conn, category="places")
    row = get_lore_entry(conn, eid)
    assert row["category"] == "places"


# ── get_lore_entry ────────────────────────────────────────────────────────────


def test_get_returns_none_for_missing(conn):
    assert get_lore_entry(conn, "inesistente") is None


def test_get_returns_dict(conn):
    eid = _add(conn, title="Yggdrasil")
    row = get_lore_entry(conn, eid)
    assert isinstance(row, dict)
    assert row["id"] == eid


# ── list_lore_entries ─────────────────────────────────────────────────────────


def test_list_empty(conn):
    assert list_lore_entries(conn) == []


def test_list_all(conn):
    _add(conn, title="A", category="places")
    _add(conn, title="B", category="world_setting")
    result = list_lore_entries(conn)
    assert len(result) == 2


def test_list_filtered_by_category(conn):
    _add(conn, title="A", category="places")
    _add(conn, title="B", category="world_setting")
    result = list_lore_entries(conn, category="places")
    assert len(result) == 1
    assert result[0]["title"] == "A"


def test_list_unknown_category_empty(conn):
    _add(conn, title="A", category="places")
    result = list_lore_entries(conn, category="altra_categoria")
    assert result == []


# ── update_lore_entry ─────────────────────────────────────────────────────────


def test_update_returns_false_for_missing(conn):
    assert update_lore_entry(conn, "nope", title="X") is False


def test_update_title(conn):
    eid = _add(conn, title="Vecchio")
    result = update_lore_entry(conn, eid, title="Nuovo")
    assert result is True
    row = get_lore_entry(conn, eid)
    assert row["title"] == "Nuovo"


def test_update_content(conn):
    eid = _add(conn, content="vecchio")
    update_lore_entry(conn, eid, content_text="nuovo testo")
    row = get_lore_entry(conn, eid)
    assert row["content_text"] == "nuovo testo"


def test_update_category(conn):
    eid = _add(conn, category="other")
    update_lore_entry(conn, eid, category="places")
    row = get_lore_entry(conn, eid)
    assert row["category"] == "places"


def test_update_no_fields_still_true(conn):
    eid = _add(conn)
    assert update_lore_entry(conn, eid) is True


# ── delete_lore_entry ─────────────────────────────────────────────────────────


def test_delete_returns_true(conn):
    eid = _add(conn)
    assert delete_lore_entry(conn, eid) is True


def test_delete_removes_entry(conn):
    eid = _add(conn)
    delete_lore_entry(conn, eid)
    assert get_lore_entry(conn, eid) is None


def test_delete_returns_false_for_missing(conn):
    assert delete_lore_entry(conn, "nonexistent") is False


# ── link_lore_to_arc / list_lore_for_arc ──────────────────────────────────────


def test_link_and_list_lore_for_arc(conn):
    arc_id = new_id()
    conn.execute(
        "INSERT INTO arcs(id, title, created_at, updated_at) "
        "VALUES(?,?,datetime('now'),datetime('now'))",
        (arc_id, "Arco Test"),
    )
    conn.commit()
    eid1 = _add(conn, title="Lore A")
    eid2 = _add(conn, title="Lore B")
    link_lore_to_arc(conn, arc_id, eid1)
    link_lore_to_arc(conn, arc_id, eid2)
    result = list_lore_for_arc(conn, arc_id)
    assert len(result) == 2
    titles = {r["title"] for r in result}
    assert "Lore A" in titles and "Lore B" in titles


def test_list_lore_for_arc_empty(conn):
    arc_id = new_id()
    conn.execute(
        "INSERT INTO arcs(id, title, created_at, updated_at) "
        "VALUES(?,?,datetime('now'),datetime('now'))",
        (arc_id, "Arc Empty"),
    )
    conn.commit()
    assert list_lore_for_arc(conn, arc_id) == []
