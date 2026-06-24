"""
Unit test per app/db/reactions.py — add_reaction, list_reactions.

Usa la fixture db_connection (SQLite in-memory con schema completo).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.characters import add_character, add_character_to_scene
from app.db.messages import add_message
from app.db.reactions import add_reaction, list_reactions
from tests.unit.conftest import add_scene


# ── helpers ───────────────────────────────────────────────────────────────────

def _setup(conn):
    """Crea scena + personaggio + messaggio; ritorna (scene_id, char_id, message_id)."""
    scene_id = add_scene(conn, title="Scena reazioni")
    char_id = add_character(conn, name="Aurora")
    add_character_to_scene(conn, scene_id, char_id)
    message_id = add_message(conn, scene_id=scene_id, author_name="Aurora", content_original="Ciao")
    return scene_id, char_id, message_id


# ── add_reaction ──────────────────────────────────────────────────────────────

def test_add_reaction_returns_id(db_connection):
    conn = db_connection["conn"]
    _, char_id, message_id = _setup(conn)
    reaction_id = add_reaction(conn, message_id=message_id, character_id=char_id, emoji="❤️")
    assert reaction_id and isinstance(reaction_id, str)


def test_add_reaction_with_emoji(db_connection):
    conn = db_connection["conn"]
    _, char_id, message_id = _setup(conn)
    add_reaction(conn, message_id=message_id, character_id=char_id, emoji="🔥")
    reactions = list_reactions(conn, message_id=message_id)
    assert reactions[0]["emoji"] == "🔥"


def test_add_reaction_empty_emoji(db_connection):
    conn = db_connection["conn"]
    _, char_id, message_id = _setup(conn)
    reaction_id = add_reaction(conn, message_id=message_id, character_id=char_id, emoji="")
    assert reaction_id is not None


def test_add_multiple_reactions(db_connection):
    conn = db_connection["conn"]
    _, char_id, message_id = _setup(conn)
    add_reaction(conn, message_id=message_id, character_id=char_id, emoji="❤️")
    add_reaction(conn, message_id=message_id, character_id=char_id, emoji="😢")
    reactions = list_reactions(conn, message_id=message_id)
    assert len(reactions) == 2


# ── list_reactions ────────────────────────────────────────────────────────────

def test_list_reactions_empty(db_connection):
    conn = db_connection["conn"]
    reactions = list_reactions(conn, message_id="msg-not-existent")
    assert reactions == []


def test_list_reactions_has_required_fields(db_connection):
    conn = db_connection["conn"]
    _, char_id, message_id = _setup(conn)
    add_reaction(conn, message_id=message_id, character_id=char_id, emoji="⚡")
    reactions = list_reactions(conn, message_id=message_id)
    row = reactions[0]
    assert "id" in row
    assert "message_id" in row
    assert "character_id" in row
    assert "emoji" in row


def test_list_reactions_filtered_by_message(db_connection):
    conn = db_connection["conn"]
    scene_id = add_scene(conn, title="Scena 2")
    char_id = add_character(conn, name="B")
    add_character_to_scene(conn, scene_id, char_id)
    msg_a = add_message(conn, scene_id=scene_id, author_name="B", content_original="A")
    msg_b = add_message(conn, scene_id=scene_id, author_name="B", content_original="B")
    add_reaction(conn, message_id=msg_a, character_id=char_id, emoji="👍")
    add_reaction(conn, message_id=msg_b, character_id=char_id, emoji="👎")
    assert len(list_reactions(conn, message_id=msg_a)) == 1
    assert list_reactions(conn, message_id=msg_a)[0]["emoji"] == "👍"
