"""Tests for duplicate_scene."""
from __future__ import annotations

from app.db.messages import add_message, duplicate_scene, list_messages_for_scene
from tests.unit.conftest import add_scene, add_character


def test_duplicate_scene_creates_new_scene_with_messages(msg_conn):
    src_id = add_scene(msg_conn, "Scena Originale")
    char_id = add_character(msg_conn, "Eroe")

    add_message(msg_conn, scene_id=src_id, character_id=char_id,
                author_name="Eroe", content_original="L1", position_order=1)
    add_message(msg_conn, scene_id=src_id, character_id=char_id,
                author_name="Eroe", content_original="L2", position_order=2)
    add_message(msg_conn, scene_id=src_id, character_id=char_id,
                author_name="Eroe", content_original="L3", position_order=3)

    new_id = duplicate_scene(msg_conn, src_id, "Variante")

    new_msgs = list_messages_for_scene(msg_conn, new_id)
    assert len(new_msgs) == 3
    assert [m["content_original"] for m in new_msgs] == ["L1", "L2", "L3"]
    assert [m["position_order"] for m in new_msgs] == [1, 2, 3]

    src_msgs = list_messages_for_scene(msg_conn, src_id)
    src_ids = {m["id"] for m in src_msgs}
    new_ids = {m["id"] for m in new_msgs}
    assert src_ids.isdisjoint(new_ids)
    assert len(src_msgs) == 3


def test_duplicate_nonexistent_source_creates_empty_scene(msg_conn):
    new_id = duplicate_scene(msg_conn, "nonexistent", "Vuota")
    msgs = list_messages_for_scene(msg_conn, new_id)
    assert len(msgs) == 0
