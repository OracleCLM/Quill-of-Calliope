"""Tests for merge_scenes."""
from __future__ import annotations

from app.db.messages import add_message, count_messages_for_scene, list_messages_for_scene, merge_scenes
from tests.unit.conftest import add_scene, add_character


def test_merge_scenes_basic(msg_conn):
    char_id = add_character(msg_conn)
    scene_a = add_scene(msg_conn, "Scene A")
    scene_b = add_scene(msg_conn, "Scene B")

    id_a1 = add_message(msg_conn, scene_id=scene_a, character_id=char_id,
                        author_name="X", content_original="A1", position_order=1)
    id_a2 = add_message(msg_conn, scene_id=scene_a, character_id=char_id,
                        author_name="X", content_original="A2", position_order=2)
    id_b1 = add_message(msg_conn, scene_id=scene_b, character_id=char_id,
                        author_name="X", content_original="B1", position_order=1)

    new_scene_id = merge_scenes(msg_conn, scene_a, scene_b, "Merged")

    merged_msgs = list_messages_for_scene(msg_conn, new_scene_id)
    assert len(merged_msgs) == 3
    assert [m["content_original"] for m in merged_msgs] == ["A1", "A2", "B1"]
    assert [m["position_order"] for m in merged_msgs] == [1, 2, 3]

    merged_ids = [m["id"] for m in merged_msgs]
    assert id_a1 not in merged_ids
    assert id_a2 not in merged_ids
    assert id_b1 not in merged_ids

    assert count_messages_for_scene(msg_conn, scene_a) == 2
    assert count_messages_for_scene(msg_conn, scene_b) == 1
