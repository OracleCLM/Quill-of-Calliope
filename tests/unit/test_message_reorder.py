"""Tests for move_message."""
from __future__ import annotations

from app.db.messages import add_message, list_messages_for_scene, move_message
from tests.unit.conftest import add_scene, add_character


def test_move_message_rebalance(msg_conn):
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)

    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="X", content_original="A", position_order=1)
    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="X", content_original="B", position_order=2)
    msg_c_id = add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                           author_name="X", content_original="C", position_order=3)

    assert move_message(msg_conn, msg_c_id, 1) is True

    messages = list_messages_for_scene(msg_conn, scene_id)
    assert [m["content_original"] for m in messages] == ["C", "A", "B"]
    assert [m["position_order"] for m in messages] == [1, 2, 3]
