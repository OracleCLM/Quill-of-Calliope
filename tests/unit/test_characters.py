"""Acceptance contract for app/db/characters.py — character CRUD + scene membership.

Pre-written by the orchestrator (characters are core to the scene-as-chat model) so a
cost-zero worker implements app/db/characters.py to satisfy THESE assertions — the
contract is authored here, not by the worker, so green = real behaviour (no toy).

Raw sqlite3 only (matches app/db/reactions.py, lore.py, __init__.py). NO sqlalchemy.

Required app/db/characters.py public API (raw sqlite3, conn-first, ids via app.db.new_id):
  add_character(conn, *, name, kind="npc", card_json=None, image_path=None) -> str
  get_character(conn, character_id) -> dict | None
  list_characters(conn, kind=None) -> list[dict]
  update_character(conn, character_id, *, name=None, card_json=None, image_path=None, kind=None) -> bool
  delete_character(conn, character_id) -> bool
  add_character_to_scene(conn, scene_id, character_id, role="participant") -> None
  list_characters_in_scene(conn, scene_id) -> list[dict]
  remove_character_from_scene(conn, scene_id, character_id) -> bool
"""
import sqlite3
import tempfile
from pathlib import Path

import pytest

import app.db as db_mod
from app.db.characters import (
    add_character,
    get_character,
    list_characters,
    update_character,
    delete_character,
    add_character_to_scene,
    list_characters_in_scene,
    remove_character_from_scene,
)

KINDS = ["operator", "player", "npc"]


@pytest.fixture
def db_connection():
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        db_path = Path(tf.name)
    conn = sqlite3.connect(str(db_path))
    try:
        db_mod.init_schema(conn)
        scene_id = db_mod.new_id()
        conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "Scene 1"))
        conn.commit()
        yield {"conn": conn, "scene_id": scene_id}
    finally:
        conn.close()
        db_path.unlink(missing_ok=True)


def test_add_and_get(db_connection):
    conn = db_connection["conn"]
    cid = add_character(conn, name="Aria", kind="player", card_json='{"v":3}')
    assert isinstance(cid, str) and cid
    row = get_character(conn, cid)
    assert row is not None
    assert row["name"] == "Aria"
    assert row["kind"] == "player"
    assert row["card_json"] == '{"v":3}'


def test_default_kind_is_npc(db_connection):
    conn = db_connection["conn"]
    cid = add_character(conn, name="Goblin")
    assert get_character(conn, cid)["kind"] == "npc"


def test_all_kinds_accepted(db_connection):
    conn = db_connection["conn"]
    for k in KINDS:
        cid = add_character(conn, name=f"c-{k}", kind=k)
        assert get_character(conn, cid)["kind"] == k


def test_invalid_kind_rejected(db_connection):
    conn = db_connection["conn"]
    with pytest.raises(sqlite3.IntegrityError):
        add_character(conn, name="bad", kind="dragon")


def test_list_all_and_by_kind(db_connection):
    conn = db_connection["conn"]
    add_character(conn, name="a", kind="npc")
    add_character(conn, name="b", kind="npc")
    add_character(conn, name="c", kind="player")
    assert len(list_characters(conn)) == 3
    npcs = list_characters(conn, kind="npc")
    assert {r["name"] for r in npcs} == {"a", "b"}


def test_update(db_connection):
    conn = db_connection["conn"]
    cid = add_character(conn, name="old", kind="npc")
    assert update_character(conn, cid, name="new", kind="player") is True
    row = get_character(conn, cid)
    assert row["name"] == "new"
    assert row["kind"] == "player"


def test_delete(db_connection):
    conn = db_connection["conn"]
    cid = add_character(conn, name="temp")
    assert delete_character(conn, cid) is True
    assert get_character(conn, cid) is None


def test_scene_membership(db_connection):
    conn = db_connection["conn"]
    scene_id = db_connection["scene_id"]
    c1 = add_character(conn, name="in-1", kind="player")
    c2 = add_character(conn, name="in-2", kind="npc")
    add_character(conn, name="out", kind="npc")
    add_character_to_scene(conn, scene_id, c1)
    add_character_to_scene(conn, scene_id, c2, role="lead")
    members = list_characters_in_scene(conn, scene_id)
    assert {r["name"] for r in members} == {"in-1", "in-2"}
    assert remove_character_from_scene(conn, scene_id, c1) is True
    assert {r["name"] for r in list_characters_in_scene(conn, scene_id)} == {"in-2"}
