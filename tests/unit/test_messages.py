"""Tests for app/db/messages.py — sqlite3 raw (post-refactor)."""
from __future__ import annotations

from app.db.messages import (
    add_message,
    compact_scene_positions,
    count_messages_for_scene,
    delete_message,
    duplicate_scene,
    get_message_by_id,
    get_scene_message_page,
    insert_message_at,
    list_messages_for_scene,
    merge_scenes,
    move_message,
    move_message_to_scene,
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


def test_insert_message_at_shifts_existing(msg_conn):
    """insert_message_at sposta i messaggi esistenti alla posizione data."""
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)

    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="A", content_original="primo", position_order=1)
    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="A", content_original="secondo", position_order=2)

    # inserisce a posizione 1 → spinge gli altri avanti
    insert_message_at(msg_conn, scene_id=scene_id, character_id=char_id,
                      author_name="A", content_original="nuovo_primo", position_order=1)

    msgs = list_messages_for_scene(msg_conn, scene_id)
    assert msgs[0]["content_original"] == "nuovo_primo"
    assert len(msgs) == 3


def test_delete_message(msg_conn):
    """delete_message rimuove il messaggio e restituisce True; id inesistente → False."""
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)

    msg_id = add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                         author_name="A", content_original="da eliminare", position_order=1)

    assert delete_message(msg_conn, msg_id) is True
    assert get_message_by_id(msg_conn, msg_id) is None
    assert delete_message(msg_conn, "non-existent") is False


def test_get_scene_message_page(msg_conn):
    """get_scene_message_page restituisce la pagina corretta."""
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)

    for i in range(5):
        add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                    author_name="A", content_original=f"msg{i}", position_order=i)

    page = get_scene_message_page(msg_conn, scene_id, page=1, per_page=3)
    assert len(page["messages"]) == 3
    assert page["total"] == 5
    assert page["page"] == 1

    page2 = get_scene_message_page(msg_conn, scene_id, page=2, per_page=3)
    assert len(page2["messages"]) == 2


def test_move_message(msg_conn):
    """move_message cambia position_order e riordina la scena."""
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)

    m1 = add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                     author_name="A", content_original="primo", position_order=1)
    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="A", content_original="secondo", position_order=2)

    result = move_message(msg_conn, m1, 2)
    assert result is True

    msgs = list_messages_for_scene(msg_conn, scene_id)
    contents = [m["content_original"] for m in msgs]
    assert "primo" in contents


def test_compact_scene_positions(msg_conn):
    """compact_scene_positions elimina gap nelle posizioni."""
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)

    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="A", content_original="a", position_order=10)
    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="A", content_original="b", position_order=20)

    count = compact_scene_positions(msg_conn, scene_id)
    assert count == 2

    msgs = list_messages_for_scene(msg_conn, scene_id)
    positions = [m["position_order"] for m in msgs]
    assert positions == sorted(positions)
    assert max(positions) < 10


def test_move_message_to_scene(msg_conn):
    """move_message_to_scene trasferisce un messaggio a un'altra scena."""
    scene_a = add_scene(msg_conn, "SceneA")
    scene_b = add_scene(msg_conn, "SceneB")
    char_id = add_character(msg_conn)

    msg_id = add_message(msg_conn, scene_id=scene_a, character_id=char_id,
                         author_name="A", content_original="da spostare", position_order=1)

    result = move_message_to_scene(msg_conn, msg_id, scene_b, new_position=1)
    assert result is True

    assert count_messages_for_scene(msg_conn, scene_a) == 0
    msgs_b = list_messages_for_scene(msg_conn, scene_b)
    assert any(m["content_original"] == "da spostare" for m in msgs_b)


def test_duplicate_scene(msg_conn):
    """duplicate_scene copia la scena con tutti i messaggi."""
    scene_id = add_scene(msg_conn, "Originale")
    char_id = add_character(msg_conn)

    add_message(msg_conn, scene_id=scene_id, character_id=char_id,
                author_name="A", content_original="msg originale", position_order=1)

    new_id = duplicate_scene(msg_conn, scene_id, new_name="Copia")
    assert new_id != scene_id

    msgs_orig = list_messages_for_scene(msg_conn, scene_id)
    msgs_copy = list_messages_for_scene(msg_conn, new_id)
    assert len(msgs_orig) == len(msgs_copy) == 1
    assert msgs_copy[0]["content_original"] == "msg originale"


def test_merge_scenes(msg_conn):
    """merge_scenes unisce i messaggi di due scene in una nuova."""
    scene_a = add_scene(msg_conn, "SceneA")
    scene_b = add_scene(msg_conn, "SceneB")
    char_id = add_character(msg_conn)

    add_message(msg_conn, scene_id=scene_a, character_id=char_id,
                author_name="A", content_original="da A", position_order=1)
    add_message(msg_conn, scene_id=scene_b, character_id=char_id,
                author_name="A", content_original="da B", position_order=1)

    merged_id = merge_scenes(msg_conn, scene_a, scene_b, new_name="Merged")
    merged_msgs = list_messages_for_scene(msg_conn, merged_id)
    contents = {m["content_original"] for m in merged_msgs}
    assert "da A" in contents
    assert "da B" in contents
