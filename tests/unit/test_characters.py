"""
Unit test per app/db/characters.py — CRUD personaggi e roster scena.

Contratto:
  - add_character: name vuoto/lungo → ValueError; valid → id UUID; kind/card_json
  - get_character: found/not found
  - list_characters: empty, kind filter, all
  - update_character: partial update, not found → False, no fields → True
  - delete_character: found → True, not found → False
  - add_character_to_scene + list_characters_in_scene: join query, role
  - update_character_scene_role: found → True, not found → False
  - remove_character_from_scene: found → True, not found → False
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.characters import (
    add_character,
    add_character_to_scene,
    delete_character,
    get_character,
    list_characters,
    list_characters_in_scene,
    remove_character_from_scene,
    update_character,
    update_character_scene_role,
)
from tests.unit.conftest import add_scene


# ── helpers ───────────────────────────────────────────────────────────────────

def _add(conn, name="Aurora", kind="npc") -> str:
    return add_character(conn, name=name, kind=kind)


# ── add_character ─────────────────────────────────────────────────────────────

def test_add_character_with_empty_name(db_connection):
    conn = db_connection["conn"]
    with pytest.raises(ValueError):
        add_character(conn, name="")


def test_add_character_with_long_name(db_connection):
    conn = db_connection["conn"]
    with pytest.raises(ValueError):
        add_character(conn, name="a" * 256)


def test_add_character_returns_id(db_connection):
    conn = db_connection["conn"]
    char_id = _add(conn)
    assert char_id and isinstance(char_id, str)


def test_add_character_kind_stored(db_connection):
    conn = db_connection["conn"]
    char_id = add_character(conn, name="GM", kind="operator")
    char = get_character(conn, char_id)
    assert char["kind"] == "operator"


def test_add_character_card_json(db_connection):
    conn = db_connection["conn"]
    char_id = add_character(conn, name="Aurora", card_json='{"desc":"strega"}')
    char = get_character(conn, char_id)
    assert char["card_json"] == '{"desc":"strega"}'


# ── get_character ─────────────────────────────────────────────────────────────

def test_get_character_found(db_connection):
    conn = db_connection["conn"]
    char_id = _add(conn, name="Aurora")
    char = get_character(conn, char_id)
    assert char is not None
    assert char["name"] == "Aurora"


def test_get_character_not_found(db_connection):
    conn = db_connection["conn"]
    assert get_character(conn, "ghost-id") is None


# ── list_characters ───────────────────────────────────────────────────────────

def test_list_characters_empty(db_connection):
    conn = db_connection["conn"]
    assert list_characters(conn) == []


def test_list_characters_all(db_connection):
    conn = db_connection["conn"]
    _add(conn, name="A")
    _add(conn, name="B")
    chars = list_characters(conn)
    assert len(chars) == 2


def test_list_characters_kind_filter(db_connection):
    conn = db_connection["conn"]
    add_character(conn, name="Player1", kind="player")
    add_character(conn, name="NPC1", kind="npc")
    players = list_characters(conn, kind="player")
    assert len(players) == 1
    assert players[0]["name"] == "Player1"


# ── update_character ──────────────────────────────────────────────────────────

def test_update_character_name(db_connection):
    conn = db_connection["conn"]
    char_id = _add(conn, name="Vecchio")
    result = update_character(conn, char_id, name="Nuovo")
    assert result is True
    assert get_character(conn, char_id)["name"] == "Nuovo"


def test_update_character_kind(db_connection):
    conn = db_connection["conn"]
    char_id = _add(conn, kind="npc")
    update_character(conn, char_id, kind="player")
    assert get_character(conn, char_id)["kind"] == "player"


def test_update_character_not_found(db_connection):
    conn = db_connection["conn"]
    assert update_character(conn, "ghost", name="x") is False


def test_update_character_no_fields_returns_true(db_connection):
    conn = db_connection["conn"]
    char_id = _add(conn)
    assert update_character(conn, char_id) is True


# ── delete_character ──────────────────────────────────────────────────────────

def test_delete_character_returns_true(db_connection):
    conn = db_connection["conn"]
    char_id = _add(conn)
    assert delete_character(conn, char_id) is True
    assert get_character(conn, char_id) is None


def test_delete_character_not_found(db_connection):
    conn = db_connection["conn"]
    assert delete_character(conn, "ghost") is False


# ── add_character_to_scene / list_characters_in_scene ─────────────────────────

def test_list_characters_in_scene_empty(db_connection):
    conn = db_connection["conn"]
    scene_id = add_scene(conn)
    assert list_characters_in_scene(conn, scene_id) == []


def test_add_character_to_scene_and_list(db_connection):
    conn = db_connection["conn"]
    scene_id = add_scene(conn)
    char_id = _add(conn, name="Aurora")
    add_character_to_scene(conn, scene_id, char_id, role="protagonist")
    chars = list_characters_in_scene(conn, scene_id)
    assert len(chars) == 1
    assert chars[0]["name"] == "Aurora"
    assert chars[0]["role"] == "protagonist"


def test_list_characters_in_scene_nonexistent(db_connection):
    conn = db_connection["conn"]
    assert list_characters_in_scene(conn, "no-scene") == []


# ── update_character_scene_role ───────────────────────────────────────────────

def test_update_character_scene_role_found(db_connection):
    conn = db_connection["conn"]
    scene_id = add_scene(conn)
    char_id = _add(conn, name="Aurora")
    add_character_to_scene(conn, scene_id, char_id, role="participant")
    result = update_character_scene_role(conn, scene_id, char_id, role="protagonist")
    assert result is True
    chars = list_characters_in_scene(conn, scene_id)
    assert chars[0]["role"] == "protagonist"


def test_update_character_scene_role_not_found(db_connection):
    conn = db_connection["conn"]
    assert update_character_scene_role(conn, "no-scene", "no-char", role="x") is False


# ── remove_character_from_scene ───────────────────────────────────────────────

def test_remove_character_from_scene_found(db_connection):
    conn = db_connection["conn"]
    scene_id = add_scene(conn)
    char_id = _add(conn)
    add_character_to_scene(conn, scene_id, char_id)
    assert remove_character_from_scene(conn, scene_id, char_id) is True
    assert list_characters_in_scene(conn, scene_id) == []


def test_remove_character_from_scene_not_found(db_connection):
    conn = db_connection["conn"]
    assert remove_character_from_scene(conn, "no-scene", "no-char") is False
