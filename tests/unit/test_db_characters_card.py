"""GAP-34: test unitari per app/db/characters — load_card_v2, save_card_v2, card_get, card_ext, empty_card_v2."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from app.db import get_db, init_schema
from app.db.characters import (
    add_character,
    card_ext,
    card_get,
    card_set,
    empty_card_v2,
    load_card_v2,
    save_card_v2,
)


@pytest.fixture
def conn(tmp_path):
    c = get_db(str(tmp_path / "test.db"))
    init_schema(c)
    yield c
    c.close()


def _add(conn, name):
    return add_character(conn, name=name, kind="npc")


# --- empty_card_v2 -----------------------------------------------------------


def test_empty_card_v2_spec():
    card = empty_card_v2("Aria")
    assert card["spec"] == "chara_card_v2"
    assert card["data"]["name"] == "Aria"


def test_empty_card_v2_has_calliope_extensions():
    card = empty_card_v2("X")
    assert "calliope" in card["data"]["extensions"]


# --- load_card_v2 ------------------------------------------------------------


def test_load_card_v2_returns_none_for_missing_char(conn):
    assert load_card_v2(conn, "InesistentePQ") is None


def test_load_card_v2_returns_skeleton_when_card_json_null(conn):
    _add(conn, "Aurora")
    card = load_card_v2(conn, "Aurora")
    assert card is not None
    assert card["data"]["name"] == "Aurora"


def test_load_card_v2_returns_saved_card(conn):
    _add(conn, "Koko")
    payload = json.dumps({
        "spec": "chara_card_v2",
        "spec_version": "2.0",
        "data": {"name": "Koko", "description": "artista"},
    })
    conn.execute("UPDATE characters SET card_json = ? WHERE name = ?", (payload, "Koko"))
    conn.commit()
    card = load_card_v2(conn, "Koko")
    assert card["data"]["description"] == "artista"


def test_load_card_v2_invalid_json_returns_skeleton(conn):
    _add(conn, "Broken")
    conn.execute("UPDATE characters SET card_json = ? WHERE name = ?", ("{{not-json}}", "Broken"))
    conn.commit()
    card = load_card_v2(conn, "Broken")
    assert card is not None
    assert card["data"]["name"] == "Broken"


# --- save_card_v2 ------------------------------------------------------------


def test_save_card_v2_returns_false_for_missing_char(conn):
    card = empty_card_v2("Ghost")
    assert save_card_v2(conn, "Ghost", card) is False


def test_save_card_v2_returns_true_and_persists(conn):
    _add(conn, "Mao")
    card = empty_card_v2("Mao")
    card["data"]["description"] = "mago oscuro"
    result = save_card_v2(conn, "Mao", card)
    assert result is True
    loaded = load_card_v2(conn, "Mao")
    assert loaded["data"]["description"] == "mago oscuro"


def test_save_card_v2_round_trip(conn):
    _add(conn, "RT")
    card = empty_card_v2("RT")
    card["data"]["personality"] = "stoica"
    card["data"]["extensions"]["calliope"]["speech_pattern"] = "arcaico"
    save_card_v2(conn, "RT", card)
    loaded = load_card_v2(conn, "RT")
    assert loaded["data"]["personality"] == "stoica"
    assert loaded["data"]["extensions"]["calliope"]["speech_pattern"] == "arcaico"


# --- card_get / card_set / card_ext ------------------------------------------


def test_card_get_returns_field_value():
    card = empty_card_v2("X")
    card["data"]["description"] = "guerriera"
    assert card_get(card, "description") == "guerriera"


def test_card_get_returns_default_for_missing():
    card = empty_card_v2("X")
    assert card_get(card, "nonexistent", default="fallback") == "fallback"


def test_card_get_safe_on_bad_card():
    assert card_get({}, "description", "def") == "def"
    assert card_get(None, "description", "def") == "def"


def test_card_set_creates_data_if_missing():
    card = {}
    card_set(card, "name", "Z")
    assert card["data"]["name"] == "Z"


def test_card_ext_returns_calliope_dict():
    card = empty_card_v2("Y")
    card["data"]["extensions"]["calliope"]["tone"] = "brusco"
    ext = card_ext(card)
    assert ext["tone"] == "brusco"


def test_card_ext_returns_empty_for_missing_ns():
    card = empty_card_v2("Y")
    ext = card_ext(card, ns="altra_estensione")
    assert ext == {}


def test_card_ext_safe_on_bad_card():
    assert card_ext({}) == {}
    assert card_ext({"data": {}}) == {}
