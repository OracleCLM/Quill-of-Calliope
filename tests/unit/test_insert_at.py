"""Tests for insert_message_at."""
from __future__ import annotations

from app.db.messages import add_message, insert_message_at, list_messages_for_scene
from tests.unit.conftest import add_scene, add_character


def test_insert_message_at_shifts_existing(msg_conn):
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)

    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="X", content_original="A", position_order=1)
    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="X", content_original="B", position_order=2)
    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="X", content_original="C", position_order=3)

    insert_message_at(msg_conn, scene_id=scene_id, character_id=char_id,
                      author_name="X", content_original="X", position_order=2)

    messages = list_messages_for_scene(msg_conn, scene_id)
    assert [m["content_original"] for m in messages] == ["A", "X", "B", "C"]
    assert [m["position_order"] for m in messages] == [1, 2, 3, 4]
