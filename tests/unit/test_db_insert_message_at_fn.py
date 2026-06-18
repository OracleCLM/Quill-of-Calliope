"""GAP-66: test estesi per insert_message_at — edge case e invarianti."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.messages import add_message, get_message_by_id, insert_message_at, list_messages_for_scene
from tests.unit.conftest import add_character, add_scene


def test_insert_returns_message_id(msg_conn):
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)
    mid = insert_message_at(msg_conn, scene_id=scene_id, character_id=char_id,
                             author_name="A", content_original="hello", position_order=1)
    assert mid
    assert isinstance(mid, str)


def test_insert_message_persisted(msg_conn):
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)
    mid = insert_message_at(msg_conn, scene_id=scene_id, character_id=char_id,
                             author_name="Aurora", content_original="Scene opens.",
                             position_order=1)
    row = get_message_by_id(msg_conn, mid)
    assert row["content_original"] == "Scene opens."
    assert row["author_name"] == "Aurora"


def test_insert_at_position_one_shifts_all(msg_conn):
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)
    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="X", content_original="First", position_order=1)
    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="X", content_original="Second", position_order=2)
    insert_message_at(msg_conn, scene_id=scene_id, character_id=char_id,
                      author_name="X", content_original="New First", position_order=1)
    messages = list_messages_for_scene(msg_conn, scene_id)
    assert messages[0]["content_original"] == "New First"
    assert messages[0]["position_order"] == 1
    assert messages[1]["content_original"] == "First"
    assert messages[1]["position_order"] == 2


def test_insert_at_end_no_shift(msg_conn):
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)
    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="X", content_original="Only", position_order=1)
    insert_message_at(msg_conn, scene_id=scene_id, character_id=char_id,
                      author_name="X", content_original="New Last", position_order=2)
    messages = list_messages_for_scene(msg_conn, scene_id)
    assert messages[0]["position_order"] == 1
    assert messages[1]["content_original"] == "New Last"
    assert messages[1]["position_order"] == 2


def test_insert_into_empty_scene(msg_conn):
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)
    insert_message_at(msg_conn, scene_id=scene_id, character_id=char_id,
                      author_name="Solo", content_original="Alone.", position_order=1)
    messages = list_messages_for_scene(msg_conn, scene_id)
    assert len(messages) == 1
    assert messages[0]["content_original"] == "Alone."


def test_insert_total_count_incremented(msg_conn):
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)
    for i in range(3):
        add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                    author_name="X", content_original=f"m{i}", position_order=i + 1)
    insert_message_at(msg_conn, scene_id=scene_id, character_id=char_id,
                      author_name="X", content_original="inserted", position_order=2)
    messages = list_messages_for_scene(msg_conn, scene_id)
    assert len(messages) == 4
