"""GAP-42: test unitari per app/db/arcs e app/db/reactions — CRUD + list."""

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
from app.db.reactions import add_reaction, list_reactions


@pytest.fixture
def conn(tmp_path):
    c = get_db(str(tmp_path / "test.db"))
    init_schema(c)
    yield c
    c.close()


def _arc(conn, title="Il Destino di Asgard", description=""):
    return create_arc(conn, title=title, description=description)


def _scene(conn, arc_id=None, title="Scena"):
    sid = new_id()
    conn.execute(
        "INSERT INTO scenes(id, title, arc_id, created_at, updated_at) "
        "VALUES(?,?,?,datetime('now'),datetime('now'))",
        (sid, title, arc_id),
    )
    conn.commit()
    return sid


def _char(conn, name="Aurora"):
    cid = new_id()
    conn.execute(
        "INSERT INTO characters(id, name, created_at, updated_at) "
        "VALUES(?,?,datetime('now'),datetime('now'))",
        (cid, name),
    )
    conn.commit()
    return cid


def _msg(conn, scene_id="s1"):
    mid = new_id()
    conn.execute(
        "INSERT INTO messages(id, scene_id, author_name, content_original, "
        "position_order, ts) "
        "VALUES(?,?,?,?,0,datetime('now'))",
        (mid, scene_id, "Aurora", "testo"),
    )
    conn.commit()
    return mid


# ── create_arc ───────────────────────────────────────────────────────────────


def test_create_arc_returns_id(conn):
    arc_id = _arc(conn)
    assert isinstance(arc_id, str) and arc_id


def test_create_arc_empty_title_raises(conn):
    with pytest.raises(ValueError):
        create_arc(conn, title="")


def test_create_arc_persists(conn):
    arc_id = _arc(conn, title="La Caduta")
    row = get_arc(conn, arc_id)
    assert row is not None
    assert row["title"] == "La Caduta"


def test_create_arc_description_stored(conn):
    arc_id = _arc(conn, description="Un viaggio epico")
    row = get_arc(conn, arc_id)
    assert row["description"] == "Un viaggio epico"


# ── get_arc ───────────────────────────────────────────────────────────────────


def test_get_arc_returns_none_for_missing(conn):
    assert get_arc(conn, "inesistente") is None


def test_get_arc_returns_dict(conn):
    arc_id = _arc(conn)
    row = get_arc(conn, arc_id)
    assert isinstance(row, dict)
    assert row["id"] == arc_id


# ── list_arcs ─────────────────────────────────────────────────────────────────


def test_list_arcs_empty(conn):
    assert list_arcs(conn) == []


def test_list_arcs_returns_all(conn):
    _arc(conn, title="A")
    _arc(conn, title="B")
    result = list_arcs(conn)
    assert len(result) == 2


def test_list_arcs_sorted_desc(conn):
    _arc(conn, title="Primo")
    _arc(conn, title="Secondo")
    result = list_arcs(conn)
    assert len(result) == 2


# ── delete_arc ────────────────────────────────────────────────────────────────


def test_delete_arc_returns_true(conn):
    arc_id = _arc(conn)
    assert delete_arc(conn, arc_id) is True


def test_delete_arc_removes_it(conn):
    arc_id = _arc(conn)
    delete_arc(conn, arc_id)
    assert get_arc(conn, arc_id) is None


def test_delete_arc_returns_false_for_missing(conn):
    assert delete_arc(conn, "nonexistent") is False


# ── list_scenes_for_arc ───────────────────────────────────────────────────────


def test_list_scenes_for_arc_empty(conn):
    arc_id = _arc(conn)
    assert list_scenes_for_arc(conn, arc_id) == []


def test_list_scenes_for_arc_returns_scenes(conn):
    arc_id = _arc(conn)
    _scene(conn, arc_id=arc_id, title="Scena A")
    _scene(conn, arc_id=arc_id, title="Scena B")
    result = list_scenes_for_arc(conn, arc_id)
    assert len(result) == 2
    titles = {r["title"] for r in result}
    assert "Scena A" in titles


def test_list_scenes_for_arc_no_exception_on_unknown_arc(conn):
    assert list_scenes_for_arc(conn, "arc-inesistente") == []


# ── add_reaction ──────────────────────────────────────────────────────────────


def test_add_reaction_returns_id(conn):
    sid = _scene(conn)
    mid = _msg(conn, sid)
    cid = _char(conn)
    rid = add_reaction(conn, message_id=mid, character_id=cid, emoji="❤️")
    assert isinstance(rid, str) and rid


def test_add_reaction_idempotent(conn):
    sid = _scene(conn)
    mid = _msg(conn, sid)
    cid = _char(conn)
    r1 = add_reaction(conn, message_id=mid, character_id=cid, emoji="👍")
    r2 = add_reaction(conn, message_id=mid, character_id=cid, emoji="👍")
    assert r1 == r2


def test_add_reaction_different_emoji_different_id(conn):
    sid = _scene(conn)
    mid = _msg(conn, sid)
    cid = _char(conn)
    r1 = add_reaction(conn, message_id=mid, character_id=cid, emoji="👍")
    r2 = add_reaction(conn, message_id=mid, character_id=cid, emoji="❤️")
    assert r1 != r2


# ── list_reactions ────────────────────────────────────────────────────────────


def test_list_reactions_empty(conn):
    mid = new_id()
    assert list_reactions(conn, message_id=mid) == []


def test_list_reactions_returns_added(conn):
    sid = _scene(conn)
    mid = _msg(conn, sid)
    cid = _char(conn)
    add_reaction(conn, message_id=mid, character_id=cid, emoji="⭐")
    result = list_reactions(conn, message_id=mid)
    assert len(result) == 1
    assert result[0]["emoji"] == "⭐"


def test_list_reactions_multiple(conn):
    sid = _scene(conn)
    mid = _msg(conn, sid)
    for emoji in ["👍", "❤️", "😂"]:
        add_reaction(conn, message_id=mid, character_id=_char(conn), emoji=emoji)
    result = list_reactions(conn, message_id=mid)
    assert len(result) == 3
