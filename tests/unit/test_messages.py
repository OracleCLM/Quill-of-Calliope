"""Tests for app/db/messages.py — sqlite3 raw (post-refactor)."""
from __future__ import annotations

from app.db.messages import (
    add_message,
    count_messages_for_scene,
    get_message_by_id,
    list_messages_for_scene,
)
from tests.unit.conftest import add_character, add_scene


def test_add_and_list_messages_order(msg_conn):
    """list_messages_for_scene restituisce messaggi ordinati per position_order."""
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)

    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="TestChar", content_original="Primo (ordine 2)", position_order=2)
    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="TestChar", content_original="Secondo (ordine 1)", position_order=1)

    msgs = list_messages_for_scene(msg_conn, scene_id)
    assert [m["content_original"] for m in msgs] == [
        "Secondo (ordine 1)",
        "Primo (ordine 2)",
    ]


def test_count_messages_for_scene(msg_conn):
    """count_messages_for_scene conta correttamente."""
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)

    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="A", content_original="msg1", position_order=1)
    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="A", content_original="msg2", position_order=2)

    assert count_messages_for_scene(msg_conn, scene_id) == 2

    empty_scene_id = add_scene(msg_conn, "Empty")
    assert count_messages_for_scene(msg_conn, empty_scene_id) == 0


def test_get_message_by_id(msg_conn):
    """get_message_by_id restituisce il messaggio corretto o None."""
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)

    msg_id = add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                         author_name="A", content_original="Test messaggio", position_order=1)

    msg = get_message_by_id(msg_conn, msg_id)
    assert msg is not None
    assert msg["content_original"] == "Test messaggio"

    assert get_message_by_id(msg_conn, "non-existent-id") is None
