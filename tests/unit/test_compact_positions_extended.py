"""GAP-64: test estesi per compact_scene_positions — edge case e invarianti."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.messages import add_message, compact_scene_positions, list_messages_for_scene
from tests.unit.conftest import add_character, add_scene


def test_compact_empty_scene_returns_zero(msg_conn):
    scene_id = add_scene(msg_conn)
    result = compact_scene_positions(msg_conn, scene_id)
    assert result == 0


def test_compact_already_contiguous_no_change(msg_conn):
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)
    for i in range(1, 4):
        add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                    author_name="A", content_original=f"m{i}", position_order=i)
    compact_scene_positions(msg_conn, scene_id)
    messages = list_messages_for_scene(msg_conn, scene_id)
    assert [m["position_order"] for m in messages] == [1, 2, 3]


def test_compact_returns_message_count(msg_conn):
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)
    for pos in (5, 100, 200, 300):
        add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                    author_name="A", content_original="x", position_order=pos)
    result = compact_scene_positions(msg_conn, scene_id)
    assert result == 4


def test_compact_starts_from_one(msg_conn):
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)
    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="A", content_original="first", position_order=99)
    compact_scene_positions(msg_conn, scene_id)
    messages = list_messages_for_scene(msg_conn, scene_id)
    assert messages[0]["position_order"] == 1


def test_compact_preserves_order(msg_conn):
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)
    for pos, content in ((10, "A"), (20, "B"), (30, "C")):
        add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                    author_name="X", content_original=content, position_order=pos)
    compact_scene_positions(msg_conn, scene_id)
    messages = list_messages_for_scene(msg_conn, scene_id)
    assert [m["content_original"] for m in messages] == ["A", "B", "C"]


def test_compact_single_message_position_one(msg_conn):
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)
    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="A", content_original="solo", position_order=42)
    compact_scene_positions(msg_conn, scene_id)
    messages = list_messages_for_scene(msg_conn, scene_id)
    assert messages[0]["position_order"] == 1


def test_compact_idempotent(msg_conn):
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)
    for pos in (5, 15, 50):
        add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                    author_name="A", content_original="x", position_order=pos)
    compact_scene_positions(msg_conn, scene_id)
    compact_scene_positions(msg_conn, scene_id)
    messages = list_messages_for_scene(msg_conn, scene_id)
    assert [m["position_order"] for m in messages] == [1, 2, 3]
