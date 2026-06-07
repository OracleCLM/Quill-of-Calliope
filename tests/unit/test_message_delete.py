"""Tests for delete_message."""
from __future__ import annotations

from app.db.messages import add_message, count_messages_for_scene, delete_message, get_message_by_id
from tests.unit.conftest import add_scene, add_character


def test_delete_existing_message(msg_conn):
    """delete_message su id esistente: True, riga rimossa, count decrementato."""
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)

    msg_id = add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                         author_name="DelChar", content_original="to delete", position_order=0)
    assert count_messages_for_scene(msg_conn, scene_id) == 1

    assert delete_message(msg_conn, msg_id) is True
    assert get_message_by_id(msg_conn, msg_id) is None
    assert count_messages_for_scene(msg_conn, scene_id) == 0


def test_delete_missing_message(msg_conn):
    """delete_message su id inesistente: False."""
    assert delete_message(msg_conn, "non-existent-id") is False
