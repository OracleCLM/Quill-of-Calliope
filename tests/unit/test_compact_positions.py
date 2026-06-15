"""Tests for compact_scene_positions."""
from __future__ import annotations

from app.db.messages import add_message, compact_scene_positions, list_messages_for_scene
from tests.unit.conftest import add_scene, add_character


def test_compact_positions_removes_gaps(msg_conn):
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)

    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="X", content_original="A", position_order=1)
    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="X", content_original="B", position_order=3)
    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="X", content_original="C", position_order=7)

    result = compact_scene_positions(msg_conn, scene_id)
    assert result == 3

    messages = list_messages_for_scene(msg_conn, scene_id)
    assert [m["content_original"] for m in messages] == ["A", "B", "C"]
    assert [m["position_order"] for m in messages] == [1, 2, 3]
