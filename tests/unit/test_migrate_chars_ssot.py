"""Test R-CALLIOPE-MA-CHAR-SSOT-MIGRATION — additivita', no-loss, idempotenza,
merge non-distruttivo.

Usa un DB SQLite fixture + una dir characters/ isolata (CALLIOPE_CHARS_DIR),
cosi' non tocca dati reali.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from app.db import characters as chardb
from scripts import migrate_chars_to_ssot as mig


SCHEMA = """
CREATE TABLE characters (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    card_json TEXT,
    image_path TEXT,
    kind TEXT NOT NULL DEFAULT 'npc',
    created_at TEXT DEFAULT '',
    updated_at TEXT DEFAULT ''
);
CREATE TABLE character_sheets (
    id TEXT PRIMARY KEY,
    character_name TEXT NOT NULL,
    character_id TEXT,
    content TEXT NOT NULL,
    ts TEXT,
    position_order INTEGER NOT NULL DEFAULT 0
);
"""


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.executescript(SCHEMA)
    yield c
    c.close()


@pytest.fixture()
def chars_dir(tmp_path, monkeypatch):
    d = tmp_path / "characters"
    d.mkdir()
    # YAML char ricco
    (d / "arianna.draft.yaml").write_text(
        "name: Arianna\n"
        "type: pc\n"
        "backstory: A seasoned warrior.\n"
        "traits:\n  - confident\n  - protective\n"
        "speech_pattern:\n  pov: first_person\n"
        "last_updated: 2026-05-16\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", str(d))
    # Punta anche il modulo migrazione alla dir isolata
    monkeypatch.setattr(mig, "CHARS_DIR", d)
    return d


def _seed_sheets(conn, names):
    for i, nm in enumerate(names):
        conn.execute(
            "INSERT INTO character_sheets (id, character_name, content, position_order) "
            "VALUES (?,?,?,?)",
            (f"s{i}", nm, f"Sheet content for {nm}", 0),
        )
    conn.commit()


def test_additive_and_no_loss(conn, chars_dir):
    _seed_sheets(conn, ["Aqua", "Bree"])
    # pre: nessuna riga characters
    report = mig.migrate(conn)
    post_names = {r[0] for r in conn.execute("SELECT name FROM characters")}
    # union = Arianna (yaml) + Aqua + Bree (sheets)
    assert {"Arianna", "Aqua", "Bree"}.issubset(post_names)
    assert report["post"]["no_loss"] is True
    assert report["post"]["missing_from_post"] == []
    assert report["sources"]["union_distinct_pre"] == len(post_names)


def test_idempotent(conn, chars_dir):
    _seed_sheets(conn, ["Aqua"])
    mig.migrate(conn)
    n1 = conn.execute("SELECT COUNT(*) FROM characters").fetchone()[0]
    cards1 = dict(conn.execute("SELECT name, card_json FROM characters").fetchall())
    rep2 = mig.migrate(conn)
    n2 = conn.execute("SELECT COUNT(*) FROM characters").fetchone()[0]
    cards2 = dict(conn.execute("SELECT name, card_json FROM characters").fetchall())
    assert n1 == n2  # nessuna riga nuova
    assert cards1 == cards2  # nessuna alterazione
    assert len(rep2["created"]) == 0
    assert len(rep2["merged"]) == 0


def test_card_v2_shape(conn, chars_dir):
    mig.migrate(conn)
    card = chardb.load_card_v2(conn, "Arianna")
    assert card["spec"] == "chara_card_v2"
    assert card["spec_version"] == "2.0"
    assert card["data"]["name"] == "Arianna"
    # backstory YAML -> description; traits -> personality
    assert "warrior" in card["data"]["description"].lower()
    assert "confident" in card["data"]["personality"]
    cal = card["data"]["extensions"]["calliope"]
    assert cal["kind"] == "player"  # type: pc
    assert cal["speech_pattern"]["pov"] == "first_person"


def test_merge_non_destructive(conn, chars_dir):
    # Pre-esiste un char 'Arianna' con card_json gia' popolato (campi propri)
    existing = chardb.empty_card_v2("Arianna")
    existing["data"]["description"] = "ALREADY SET — keep me"
    existing["data"]["scenario"] = "Original scenario"
    existing["data"]["extensions"]["calliope"]["custom_unknown"] = "preserve"
    conn.execute(
        "INSERT INTO characters (id, name, kind, card_json) VALUES (?,?,?,?)",
        ("x1", "Arianna", "npc", json.dumps(existing, ensure_ascii=False)),
    )
    conn.commit()

    mig.migrate(conn)
    card = chardb.load_card_v2(conn, "Arianna")
    # campo gia' presente NON sovrascritto
    assert card["data"]["description"] == "ALREADY SET — keep me"
    assert card["data"]["scenario"] == "Original scenario"
    # extension ignota preservata
    assert card["data"]["extensions"]["calliope"]["custom_unknown"] == "preserve"
    # campo vuoto riempito dal candidate (personality dai traits YAML)
    assert "confident" in card["data"]["personality"]


def test_sheets_table_untouched(conn, chars_dir):
    _seed_sheets(conn, ["Aqua", "Bree"])
    before = conn.execute(
        "SELECT id, character_name, content, position_order FROM character_sheets ORDER BY id"
    ).fetchall()
    mig.migrate(conn)
    after = conn.execute(
        "SELECT id, character_name, content, position_order FROM character_sheets ORDER BY id"
    ).fetchall()
    assert before == after


def test_load_save_helpers(conn):
    conn.execute(
        "INSERT INTO characters (id, name, kind, card_json) VALUES (?,?,?,?)",
        ("y1", "Tester", "npc", None),
    )
    conn.commit()
    # load di riga con card_json NULL -> scheletro vuoto
    card = chardb.load_card_v2(conn, "Tester")
    assert card["data"]["name"] == "Tester"
    chardb.card_set(card, "personality", "stoic")
    assert chardb.save_card_v2(conn, "Tester", card) is True
    reloaded = chardb.load_card_v2(conn, "Tester")
    assert chardb.card_get(reloaded, "personality") == "stoic"
    # save su nome inesistente -> False
    assert chardb.save_card_v2(conn, "Ghost", card) is False
    # load su nome inesistente -> None
    assert chardb.load_card_v2(conn, "Ghost") is None
