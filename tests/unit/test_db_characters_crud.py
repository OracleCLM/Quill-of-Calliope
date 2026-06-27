"""GAP-46: test unitari per app/db/characters — CRUD + Card V2 helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from app.db import get_db, init_schema, new_id
from app.db.characters import (
    CARD_V2_SPEC,
    CARD_V2_VERSION,
    add_character,
    add_character_to_scene,
    card_ext,
    card_get,
    card_set,
    delete_character,
    empty_card_v2,
    get_character,
    list_characters,
    list_characters_in_scene,
    load_card_v2,
    remove_character_from_scene,
    save_card_v2,
    update_character,
    update_character_scene_role,
)


@pytest.fixture
def conn(tmp_path):
    c = get_db(str(tmp_path / "test.db"))
    init_schema(c)
    yield c
    c.close()


def _add(conn, name="Aurora", kind="npc"):
    return add_character(conn, name=name, kind=kind)


def _scene(conn, title="Scena"):
    sid = new_id()
    conn.execute(
        "INSERT INTO scenes(id, title, created_at, updated_at) "
        "VALUES(?,?,datetime('now'),datetime('now'))",
        (sid, title),
    )
    conn.commit()
    return sid


# ── add_character ─────────────────────────────────────────────────────────────


def test_add_character_returns_id(conn):
    cid = _add(conn)
    assert isinstance(cid, str) and cid


def test_add_character_empty_name_raises(conn):
    with pytest.raises(ValueError):
        _add(conn, name="")


def test_add_character_long_name_raises(conn):
    with pytest.raises(ValueError):
        _add(conn, name="x" * 256)


def test_add_character_persists(conn):
    cid = _add(conn, name="Aurora")
    row = get_character(conn, cid)
    assert row is not None
    assert row["name"] == "Aurora"


def test_add_character_default_kind_npc(conn):
    cid = _add(conn, name="Mao")
    row = get_character(conn, cid)
    assert row["kind"] == "npc"


def test_add_character_kind_stored(conn):
    cid = _add(conn, name="Kira", kind="player")
    row = get_character(conn, cid)
    assert row["kind"] == "player"


# ── get_character ─────────────────────────────────────────────────────────────


def test_get_character_returns_none_for_missing(conn):
    assert get_character(conn, "inesistente") is None


def test_get_character_returns_dict(conn):
    cid = _add(conn)
    row = get_character(conn, cid)
    assert isinstance(row, dict)
    assert row["id"] == cid


# ── list_characters ───────────────────────────────────────────────────────────


def test_list_characters_empty(conn):
    assert list_characters(conn) == []


def test_list_characters_returns_all(conn):
    _add(conn, name="A")
    _add(conn, name="B")
    assert len(list_characters(conn)) == 2


def test_list_characters_filtered_by_kind(conn):
    _add(conn, name="Mago", kind="npc")
    _add(conn, name="Eroe", kind="player")
    result = list_characters(conn, kind="npc")
    assert all(c["kind"] == "npc" for c in result)
    assert len(result) == 1


def test_list_characters_unknown_kind_empty(conn):
    _add(conn, name="X", kind="npc")
    assert list_characters(conn, kind="ghost") == []


# ── update_character ──────────────────────────────────────────────────────────


def test_update_character_returns_false_for_missing(conn):
    assert update_character(conn, "nonexistent", name="X") is False


def test_update_character_updates_name(conn):
    cid = _add(conn, name="Vecchio")
    assert update_character(conn, cid, name="Nuovo") is True
    assert get_character(conn, cid)["name"] == "Nuovo"


def test_update_character_updates_kind(conn):
    cid = _add(conn, name="X", kind="npc")
    update_character(conn, cid, kind="operator")
    assert get_character(conn, cid)["kind"] == "operator"


def test_update_character_no_fields_returns_true(conn):
    cid = _add(conn)
    assert update_character(conn, cid) is True


# ── delete_character ──────────────────────────────────────────────────────────


def test_delete_character_returns_true(conn):
    cid = _add(conn)
    assert delete_character(conn, cid) is True


def test_delete_character_removes_it(conn):
    cid = _add(conn)
    delete_character(conn, cid)
    assert get_character(conn, cid) is None


def test_delete_character_returns_false_for_missing(conn):
    assert delete_character(conn, "nonexistent") is False


# ── empty_card_v2 ─────────────────────────────────────────────────────────────


def test_empty_card_v2_spec(conn):
    card = empty_card_v2("Aurora")
    assert card["spec"] == CARD_V2_SPEC
    assert card["spec_version"] == CARD_V2_VERSION


def test_empty_card_v2_name_set(conn):
    card = empty_card_v2("Aurora")
    assert card["data"]["name"] == "Aurora"


def test_empty_card_v2_tags_list(conn):
    card = empty_card_v2()
    assert isinstance(card["data"]["tags"], list)


# ── load_card_v2 / save_card_v2 ───────────────────────────────────────────────


def test_load_card_v2_none_for_missing(conn):
    assert load_card_v2(conn, "NessunPersonaggio") is None


def test_load_card_v2_empty_card_json_returns_skeleton(conn):
    _add(conn, name="Mao")
    card = load_card_v2(conn, "Mao")
    assert card is not None
    assert card["spec"] == CARD_V2_SPEC


def test_save_and_load_card_v2_roundtrip(conn):
    _add(conn, name="Aurora")
    original = empty_card_v2("Aurora")
    original["data"]["description"] = "Guerriera leggendaria"
    assert save_card_v2(conn, "Aurora", original) is True
    loaded = load_card_v2(conn, "Aurora")
    assert loaded["data"]["description"] == "Guerriera leggendaria"


def test_save_card_v2_returns_false_for_missing(conn):
    assert save_card_v2(conn, "NessunPersonaggio", empty_card_v2()) is False


def test_load_card_v2_invalid_json_returns_skeleton(conn):
    _add(conn, name="X")
    conn.execute("UPDATE characters SET card_json = ? WHERE name = ?", ("{invalid}", "X"))
    conn.commit()
    card = load_card_v2(conn, "X")
    assert card["spec"] == CARD_V2_SPEC


# ── card_get / card_set / card_ext ────────────────────────────────────────────


def test_card_get_returns_value():
    card = empty_card_v2("A")
    card["data"]["description"] = "testo"
    assert card_get(card, "description") == "testo"


def test_card_get_returns_default_for_missing():
    card = empty_card_v2()
    assert card_get(card, "campo_inesistente", "default") == "default"


def test_card_get_handles_non_mapping():
    assert card_get("non-card", "name", "x") == "x"


def test_card_set_stores_value():
    card = empty_card_v2()
    card_set(card, "personality", "audace")
    assert card["data"]["personality"] == "audace"


def test_card_ext_returns_calliope_ns():
    card = empty_card_v2("A")
    card["data"]["extensions"]["calliope"]["custom"] = True
    ext = card_ext(card)
    assert ext.get("custom") is True


def test_card_ext_returns_empty_for_unknown_ns():
    card = empty_card_v2()
    assert card_ext(card, ns="unknown_ns") == {}


# ── scene associations ────────────────────────────────────────────────────────


def test_add_character_to_scene_and_list(conn):
    sid = _scene(conn)
    cid = _add(conn)
    add_character_to_scene(conn, sid, cid, role="protagonist")
    chars = list_characters_in_scene(conn, sid)
    assert any(c["id"] == cid for c in chars)


def test_list_characters_in_scene_empty(conn):
    sid = _scene(conn)
    assert list_characters_in_scene(conn, sid) == []


def test_update_character_scene_role(conn):
    sid = _scene(conn)
    cid = _add(conn)
    add_character_to_scene(conn, sid, cid, role="participant")
    result = update_character_scene_role(conn, sid, cid, "antagonist")
    assert result is True
    chars = list_characters_in_scene(conn, sid)
    row = next(c for c in chars if c["id"] == cid)
    assert row["role"] == "antagonist"


def test_update_character_scene_role_not_found(conn):
    sid = _scene(conn)
    assert update_character_scene_role(conn, sid, new_id(), "antagonist") is False


def test_remove_character_from_scene(conn):
    sid = _scene(conn)
    cid = _add(conn)
    add_character_to_scene(conn, sid, cid)
    assert remove_character_from_scene(conn, sid, cid) is True
    assert list_characters_in_scene(conn, sid) == []


def test_remove_character_from_scene_not_present(conn):
    sid = _scene(conn)
    assert remove_character_from_scene(conn, sid, new_id()) is False
