"""Tests for get_scene_message_page."""
from __future__ import annotations

from app.db.messages import add_message, get_scene_message_page
from tests.unit.conftest import add_scene, add_character


def _seed(conn, n=5):
    scene_id = add_scene(conn, "PageScene")
    char_id = add_character(conn, "PageChar")
    for i in range(n):
        add_message(conn, scene_id=scene_id, character_id=char_id,
                    author_name="PageChar", content_original=f"msg-{i}", position_order=i)
    return scene_id


def test_first_page_has_more(msg_conn):
    """Prima pagina (per_page=2, page=1): total=5, 2 messaggi, has_more calcolabile."""
    scene_id = _seed(msg_conn, n=5)
    page = get_scene_message_page(msg_conn, scene_id, page=1, per_page=2)
    assert page["total"] == 5
    assert page["per_page"] == 2
    assert len(page["messages"]) == 2
    assert page["pages"] == 3
    assert [m["content_original"] for m in page["messages"]] == ["msg-0", "msg-1"]


def test_last_page_no_more(msg_conn):
    """Ultima pagina (per_page=2, page=3): 1 messaggio residuo."""
    scene_id = _seed(msg_conn, n=5)
    page = get_scene_message_page(msg_conn, scene_id, page=3, per_page=2)
    assert page["total"] == 5
    assert len(page["messages"]) == 1
    assert page["messages"][0]["content_original"] == "msg-4"
