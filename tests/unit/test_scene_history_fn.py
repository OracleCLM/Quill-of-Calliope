"""GAP-28: test unitari per write_routes._scene_history — limit, ordine, content_enhanced."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from app.db import get_db, init_schema, new_id
from app.db.messages import add_message
from app.calliope_shell.write_routes import _scene_history


@pytest.fixture
def db(tmp_path):
    conn = get_db(str(tmp_path / "test.db"))
    init_schema(conn)
    return conn


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


def _make_scene(conn):
    sid = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (sid, "ScenaTest"))
    conn.commit()
    return sid


def test_scene_history_empty_scene_id_returns_empty():
    assert _scene_history("") == ""
    assert _scene_history(None) == ""


def test_scene_history_no_messages_returns_empty(db, db_path):
    sid = _make_scene(db)
    with patch("app.db.get_db", return_value=get_db(db_path)):
        result = _scene_history(sid)
    assert result == ""


def test_scene_history_formats_author_colon_content(db, db_path):
    sid = _make_scene(db)
    add_message(db, scene_id=sid, author_name="Aria", content_original="Eccomi.", position_order=0)
    db.commit()
    with patch("app.db.get_db", return_value=get_db(db_path)):
        result = _scene_history(sid)
    assert "Aria: Eccomi." in result


def test_scene_history_multiple_messages_in_order(db, db_path):
    sid = _make_scene(db)
    add_message(db, scene_id=sid, author_name="A", content_original="primo", position_order=0)
    add_message(db, scene_id=sid, author_name="B", content_original="secondo", position_order=1)
    db.commit()
    with patch("app.db.get_db", return_value=get_db(db_path)):
        result = _scene_history(sid)
    lines = result.splitlines()
    assert len(lines) == 2
    assert lines[0] == "A: primo"
    assert lines[1] == "B: secondo"


def test_scene_history_respects_max_msgs_limit(db, db_path):
    sid = _make_scene(db)
    for i in range(10):
        add_message(db, scene_id=sid, author_name=f"C{i}", content_original=f"msg{i}", position_order=i)
    db.commit()
    with patch("app.db.get_db", return_value=get_db(db_path)):
        result = _scene_history(sid, max_msgs=3)
    lines = [ln for ln in result.splitlines() if ln.strip()]
    assert len(lines) == 3
    # ultimi 3: msg7, msg8, msg9
    assert "msg7" in result
    assert "msg9" in result
    assert "msg0" not in result


def test_scene_history_content_enhanced_fallback(db, db_path):
    """Se content_original è vuoto usa content_enhanced."""
    sid = _make_scene(db)
    add_message(db, scene_id=sid, author_name="X",
                content_original="", position_order=0,
                content_enhanced="Enhanced text.")
    db.commit()
    with patch("app.db.get_db", return_value=get_db(db_path)):
        result = _scene_history(sid)
    assert "Enhanced text." in result


def test_scene_history_skips_empty_content(db, db_path):
    sid = _make_scene(db)
    add_message(db, scene_id=sid, author_name="Y", content_original="", position_order=0)
    add_message(db, scene_id=sid, author_name="Z", content_original="valido", position_order=1)
    db.commit()
    with patch("app.db.get_db", return_value=get_db(db_path)):
        result = _scene_history(sid)
    assert "Y:" not in result
    assert "Z: valido" in result
