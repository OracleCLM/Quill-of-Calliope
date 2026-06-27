"""GAP-54: test unitari per app/db/arcs — create_arc/list_arcs/get_arc/delete_arc/list_scenes_for_arc."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from app.db import get_db, init_schema, new_id
from app.db.arcs import (
    create_arc,
    delete_arc,
    get_arc,
    list_arcs,
    list_scenes_for_arc,
)


@pytest.fixture
def conn(tmp_path):
    c = get_db(str(tmp_path / "test.db"))
    init_schema(c)
    yield c
    c.close()


def _scene(conn, title="Scena", arc_id=None):
    sid = new_id()
    conn.execute(
        "INSERT INTO scenes(id, title, arc_id, created_at, updated_at) "
        "VALUES(?,?,?,datetime('now'),datetime('now'))",
        (sid, title, arc_id),
    )
    conn.commit()
    return sid


# ── create_arc ────────────────────────────────────────────────────────────────


def test_create_arc_returns_string_id(conn):
    aid = create_arc(conn, "Arco Uno")
    assert isinstance(aid, str) and aid


def test_create_arc_empty_title_raises(conn):
    with pytest.raises(ValueError):
        create_arc(conn, "")


def test_create_arc_persists(conn):
    aid = create_arc(conn, "Persiste")
    assert get_arc(conn, aid) is not None


def test_create_arc_title_stored(conn):
    aid = create_arc(conn, "Titolo Epico")
    row = get_arc(conn, aid)
    assert row["title"] == "Titolo Epico"


def test_create_arc_description_stored(conn):
    aid = create_arc(conn, "T", description="Un grande arco narrativo")
    row = get_arc(conn, aid)
    assert row["description"] == "Un grande arco narrativo"


def test_create_arc_default_empty_description(conn):
    aid = create_arc(conn, "T")
    row = get_arc(conn, aid)
    assert row["description"] == ""


# ── list_arcs ─────────────────────────────────────────────────────────────────


def test_list_arcs_empty(conn):
    assert list_arcs(conn) == []


def test_list_arcs_returns_all(conn):
    create_arc(conn, "A")
    create_arc(conn, "B")
    assert len(list_arcs(conn)) == 2


def test_list_arcs_returns_dicts(conn):
    create_arc(conn, "X")
    result = list_arcs(conn)
    assert all(isinstance(r, dict) for r in result)


def test_list_arcs_each_has_id(conn):
    create_arc(conn, "X")
    for arc in list_arcs(conn):
        assert "id" in arc


# ── get_arc ───────────────────────────────────────────────────────────────────


def test_get_arc_none_for_missing(conn):
    assert get_arc(conn, "inesistente") is None


def test_get_arc_returns_dict(conn):
    aid = create_arc(conn, "T")
    row = get_arc(conn, aid)
    assert isinstance(row, dict)
    assert row["id"] == aid


def test_get_arc_correct_title(conn):
    aid = create_arc(conn, "Esatto")
    assert get_arc(conn, aid)["title"] == "Esatto"


# ── delete_arc ────────────────────────────────────────────────────────────────


def test_delete_arc_returns_true(conn):
    aid = create_arc(conn, "T")
    assert delete_arc(conn, aid) is True


def test_delete_arc_removes_it(conn):
    aid = create_arc(conn, "T")
    delete_arc(conn, aid)
    assert get_arc(conn, aid) is None


def test_delete_arc_missing_returns_false(conn):
    assert delete_arc(conn, "inesistente") is False


# ── list_scenes_for_arc ───────────────────────────────────────────────────────


def test_list_scenes_for_arc_empty(conn):
    aid = create_arc(conn, "T")
    assert list_scenes_for_arc(conn, aid) == []


def test_list_scenes_for_arc_returns_assigned_scenes(conn):
    aid = create_arc(conn, "T")
    sid = _scene(conn, arc_id=aid)
    result = list_scenes_for_arc(conn, aid)
    assert any(r["id"] == sid for r in result)


def test_list_scenes_for_arc_no_exception_unknown(conn):
    result = list_scenes_for_arc(conn, "arc-inesistente")
    assert result == []


def test_list_scenes_for_arc_excludes_unassigned(conn):
    aid = create_arc(conn, "T")
    _scene(conn, arc_id=None)
    assert list_scenes_for_arc(conn, aid) == []
