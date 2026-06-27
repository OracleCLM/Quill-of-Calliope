"""GAP-52: test unitari per app/db/scenes — list_scenes(filter) + assign_scene_to_arc."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from app.db import get_db, init_schema, new_id
from app.db.scenes import assign_scene_to_arc, list_scenes


@pytest.fixture
def conn(tmp_path):
    c = get_db(str(tmp_path / "test.db"))
    init_schema(c)
    yield c
    c.close()


def _add_arc(conn, title="Arco test"):
    aid = new_id()
    conn.execute(
        "INSERT INTO arcs(id, title, description, created_at) VALUES(?,?,?,datetime('now'))",
        (aid, title, ""),
    )
    conn.commit()
    return aid


def _add_scene(conn, title="Foresta Oscura", arc_id=None):
    sid = new_id()
    conn.execute(
        "INSERT INTO scenes(id, title, arc_id, created_at, updated_at) "
        "VALUES(?,?,?,datetime('now'),datetime('now'))",
        (sid, title, arc_id),
    )
    conn.commit()
    return sid


# ── list_scenes ───────────────────────────────────────────────────────────────


def test_list_scenes_empty(conn):
    assert list_scenes(conn) == []


def test_list_scenes_returns_all(conn):
    _add_scene(conn, "Prima")
    _add_scene(conn, "Seconda")
    assert len(list_scenes(conn)) == 2


def test_list_scenes_no_filter_includes_all(conn):
    _add_scene(conn, "Alfa")
    _add_scene(conn, "Beta")
    titles = {s["title"] for s in list_scenes(conn)}
    assert "Alfa" in titles and "Beta" in titles


def test_list_scenes_filter_by_title_substring(conn):
    _add_scene(conn, "Foresta Oscura")
    _add_scene(conn, "Castello in Rovina")
    result = list_scenes(conn, title_contains="Foresta")
    assert len(result) == 1
    assert result[0]["title"] == "Foresta Oscura"


def test_list_scenes_filter_no_match_returns_empty(conn):
    _add_scene(conn, "Foresta")
    assert list_scenes(conn, title_contains="inesistente") == []


def test_list_scenes_filter_partial_match(conn):
    _add_scene(conn, "La Foresta di Arda")
    _add_scene(conn, "Castello")
    result = list_scenes(conn, title_contains="Foresta")
    assert len(result) == 1


def test_list_scenes_filter_case_insensitive(conn):
    _add_scene(conn, "Foresta Oscura")
    result = list_scenes(conn, title_contains="foresta")
    assert len(result) == 1


def test_list_scenes_each_has_id_field(conn):
    _add_scene(conn, "X")
    for s in list_scenes(conn):
        assert "id" in s


def test_list_scenes_returns_dicts(conn):
    _add_scene(conn, "Y")
    result = list_scenes(conn)
    assert all(isinstance(s, dict) for s in result)


# ── assign_scene_to_arc ───────────────────────────────────────────────────────


def test_assign_scene_to_arc_returns_true(conn):
    aid = _add_arc(conn)
    sid = _add_scene(conn)
    assert assign_scene_to_arc(conn, sid, aid) is True


def test_assign_scene_to_arc_missing_scene_returns_false(conn):
    aid = _add_arc(conn)
    assert assign_scene_to_arc(conn, "inesistente", aid) is False


def test_assign_scene_to_arc_stores_arc_id(conn):
    aid = _add_arc(conn)
    sid = _add_scene(conn)
    assign_scene_to_arc(conn, sid, aid)
    row = conn.execute("SELECT arc_id FROM scenes WHERE id = ?", (sid,)).fetchone()
    assert row[0] == aid


def test_assign_scene_to_arc_none_removes_arc(conn):
    aid = _add_arc(conn)
    sid = _add_scene(conn, arc_id=aid)
    assign_scene_to_arc(conn, sid, None)
    row = conn.execute("SELECT arc_id FROM scenes WHERE id = ?", (sid,)).fetchone()
    assert row[0] is None


def test_assign_scene_to_arc_replaces_existing(conn):
    aid1 = _add_arc(conn, "Arco 1")
    aid2 = _add_arc(conn, "Arco 2")
    sid = _add_scene(conn, arc_id=aid1)
    assign_scene_to_arc(conn, sid, aid2)
    row = conn.execute("SELECT arc_id FROM scenes WHERE id = ?", (sid,)).fetchone()
    assert row[0] == aid2
