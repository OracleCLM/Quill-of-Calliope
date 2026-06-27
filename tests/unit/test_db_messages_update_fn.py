"""GAP-65: test diretti per update_message in app/db/messages.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from app.db.messages import add_message, get_message_by_id, update_message
from tests.unit.conftest import add_character, add_scene


@pytest.fixture
def seeded(msg_conn):
    scene_id = add_scene(msg_conn)
    char_id = add_character(msg_conn)
    mid = add_message(
        msg_conn, scene_id=scene_id, character_id=char_id,
        author_name="Aurora", content_original="Original text.",
    )
    return msg_conn, mid


# ── ritorno True/False ────────────────────────────────────────────────────────


def test_update_message_returns_true(seeded):
    conn, mid = seeded
    result = update_message(conn, mid, content_original="Updated.")
    assert result is True


def test_update_message_returns_false_for_missing(msg_conn):
    result = update_message(msg_conn, "msg-not-exists", content_original="x")
    assert result is False


# ── campo content_original ────────────────────────────────────────────────────


def test_update_content_original_persists(seeded):
    conn, mid = seeded
    update_message(conn, mid, content_original="New content.")
    row = get_message_by_id(conn, mid)
    assert row["content_original"] == "New content."


# ── campo author_name ─────────────────────────────────────────────────────────


def test_update_author_name_persists(seeded):
    conn, mid = seeded
    update_message(conn, mid, author_name="Mao")
    row = get_message_by_id(conn, mid)
    assert row["author_name"] == "Mao"


def test_update_author_name_does_not_change_content(seeded):
    conn, mid = seeded
    original = get_message_by_id(conn, mid)["content_original"]
    update_message(conn, mid, author_name="NewName")
    row = get_message_by_id(conn, mid)
    assert row["content_original"] == original


# ── campo content_enhanced ───────────────────────────────────────────────────


def test_update_content_enhanced_persists(seeded):
    conn, mid = seeded
    update_message(conn, mid, content_enhanced="Enhanced version.")
    row = get_message_by_id(conn, mid)
    assert row["content_enhanced"] == "Enhanced version."


def test_update_content_enhanced_does_not_touch_original(seeded):
    conn, mid = seeded
    orig = get_message_by_id(conn, mid)["content_original"]
    update_message(conn, mid, content_enhanced="Enhanced.")
    row = get_message_by_id(conn, mid)
    assert row["content_original"] == orig


# ── nessun campo ─────────────────────────────────────────────────────────────


def test_update_no_fields_raises_value_error(seeded):
    conn, mid = seeded
    with pytest.raises(ValueError):
        update_message(conn, mid)


# ── aggiornamento multiplo ────────────────────────────────────────────────────


def test_update_multiple_fields_together(seeded):
    conn, mid = seeded
    update_message(conn, mid, content_original="New.", author_name="Kira")
    row = get_message_by_id(conn, mid)
    assert row["content_original"] == "New."
    assert row["author_name"] == "Kira"
