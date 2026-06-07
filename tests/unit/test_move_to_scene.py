"""Tests for move_message_to_scene."""
from __future__ import annotations

from app.db.messages import (
    add_message,
    count_messages_for_scene,
    list_messages_for_scene,
    move_message_to_scene,
)
from tests.unit.conftest import add_character, add_scene


def test_move_message_to_scene(msg_conn):
    char_id = add_character(msg_conn)
    scene_a = add_scene(msg_conn, "Scene A")
    scene_b = add_scene(msg_conn, "Scene B")

    add_message(msg_conn, scene_id=scene_a, character_id=char_id,
                author_name="C", content_original="A1", position_order=1)
    id_a2 = add_message(msg_conn, scene_id=scene_a, character_id=char_id,
                        author_name="C", content_original="A2", position_order=2)
    add_message(msg_conn, scene_id=scene_a, character_id=char_id,
                author_name="C", content_original="A3", position_order=3)
    add_message(msg_conn, scene_id=scene_b, character_id=char_id,
                author_name="C", content_original="B1", position_order=1)
    add_message(msg_conn, scene_id=scene_b, character_id=char_id,
                author_name="C", content_original="B2", position_order=2)

    assert move_message_to_scene(msg_conn, id_a2, scene_b, 2) is True

    msgs_b = list_messages_for_scene(msg_conn, scene_b)
    assert [m["content_original"] for m in msgs_b] == ["B1", "A2", "B2"]
    assert [m["position_order"] for m in msgs_b] == [1, 2, 3]

    msgs_a = list_messages_for_scene(msg_conn, scene_a)
    assert [m["content_original"] for m in msgs_a] == ["A1", "A3"]
    assert [m["position_order"] for m in msgs_a] == [1, 2]

    count_before = count_messages_for_scene(msg_conn, scene_b)
    assert move_message_to_scene(msg_conn, "non_existent", scene_b, 1) is False
    assert count_messages_for_scene(msg_conn, scene_b) == count_before
