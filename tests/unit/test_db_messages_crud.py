"""Unit test per le funzioni CRUD core di app/db/messages.py (gap coverage)."""
import pytest
from unittest.mock import patch

from app.db import get_db, init_schema
import app.db.messages as _msg_mod
from app.db.messages import add_message, insert_message_at, update_message, move_message_to_scene


@pytest.fixture
def conn(tmp_path):
    c = get_db(tmp_path / "msg.db")
    init_schema(c)
    c.execute("INSERT INTO scenes (id, title) VALUES ('s1', 'Scena 1')")
    c.commit()
    yield c
    c.close()


# ── add_message (line 69) ─────────────────────────────────────────────────────

def test_add_message_raises_when_new_id_none(conn):
    with patch.object(_msg_mod, "new_id", None):
        with pytest.raises(RuntimeError, match="new_id function not available"):
            add_message(conn, scene_id="s1", author_name="X", content_original="y")


# ── insert_message_at (line 127) ──────────────────────────────────────────────

def test_insert_message_at_raises_when_new_id_none(conn):
    with patch.object(_msg_mod, "new_id", None):
        with pytest.raises(RuntimeError, match="new_id function not available"):
            insert_message_at(conn, scene_id="s1", author_name="X", content_original="y", position_order=0)


# ── update_message (line 372) ─────────────────────────────────────────────────

def test_update_message_raises_when_no_fields(conn):
    msg_id = add_message(conn, scene_id="s1", author_name="A", content_original="c")
    with pytest.raises(ValueError, match="nessun campo da aggiornare"):
        update_message(conn, msg_id)


# ── move_message_to_scene (line 544) ─────────────────────────────────────────

def test_move_message_to_scene_returns_false_when_not_found(conn):
    result = move_message_to_scene(conn, "nonexistent-id", "s1", 0)
    assert result is False
