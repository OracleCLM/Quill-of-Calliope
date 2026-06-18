"""GAP-67: test per _load_char_sheets in server.py — DB + YAML fallback."""

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import app.calliope_shell.server as srv


@pytest.fixture
def char_db(tmp_path):
    """Ritorna (conn, db_path) — conn per seeding, path per ricreazione."""
    db_path = tmp_path / "chars.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE characters (name TEXT PRIMARY KEY, card_json TEXT)"
    )
    conn.commit()
    return conn, db_path


def _fake_get_db(db_path):
    """Factory che crea una nuova connessione ad ogni chiamata (simula get_db)."""
    def _inner(path=None):
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        return c
    return _inner


# ── lista vuota ──────────────────────────────────────────────────────────────


def test_load_no_names_returns_empty(monkeypatch, char_db):
    _, db_path = char_db
    monkeypatch.setattr("app.db.get_db", _fake_get_db(db_path))
    result = srv._load_char_sheets([])
    assert result == []


# ── DB: nome trovato ──────────────────────────────────────────────────────────


def test_load_from_db_returns_sheet(monkeypatch, char_db):
    conn, db_path = char_db
    card = {"traits": ["coraggioso"], "backstory": "Nata in montagna.", "race": "Elfa", "class": "Ranger"}
    conn.execute(
        "INSERT INTO characters (name, card_json) VALUES (?, ?)",
        ("Elara", json.dumps(card)),
    )
    conn.commit()
    monkeypatch.setattr("app.db.get_db", _fake_get_db(db_path))
    result = srv._load_char_sheets(["Elara"])
    assert len(result) == 1
    sheet = result[0]
    assert sheet["name"] == "Elara"
    assert sheet["traits"] == ["coraggioso"]
    assert sheet["race"] == "Elfa"
    assert "Nata in montagna" in sheet["backstory"]


# ── DB: card_json malformato → valori di default ─────────────────────────────


def test_load_db_malformed_json_uses_defaults(monkeypatch, char_db):
    conn, db_path = char_db
    conn.execute(
        "INSERT INTO characters (name, card_json) VALUES (?, ?)",
        ("Broken", "{ not valid json !!!"),
    )
    conn.commit()
    monkeypatch.setattr("app.db.get_db", _fake_get_db(db_path))
    result = srv._load_char_sheets(["Broken"])
    assert len(result) == 1
    sheet = result[0]
    assert sheet["name"] == "Broken"
    assert sheet["traits"] == []
    assert sheet["backstory"] == ""


# ── DB: card_json null → valori di default ───────────────────────────────────


def test_load_db_null_json_uses_defaults(monkeypatch, char_db):
    conn, db_path = char_db
    conn.execute(
        "INSERT INTO characters (name, card_json) VALUES (?, ?)",
        ("Null", None),
    )
    conn.commit()
    monkeypatch.setattr("app.db.get_db", _fake_get_db(db_path))
    result = srv._load_char_sheets(["Null"])
    assert len(result) == 1
    assert result[0]["traits"] == []


# ── YAML fallback ─────────────────────────────────────────────────────────────


def test_load_yaml_fallback(monkeypatch, tmp_path, char_db):
    _, db_path = char_db  # DB vuoto
    yaml_dir = tmp_path / "chars"
    yaml_dir.mkdir()
    (yaml_dir / "aurora.yaml").write_text(
        "name: Aurora\ntraits:\n  - gentile\nbackstory: Cresciuta al mare.\nrace: Umana\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("app.db.get_db", _fake_get_db(db_path))
    monkeypatch.setattr(srv, "_CHARS_DIR", yaml_dir)
    result = srv._load_char_sheets(["Aurora"])
    assert len(result) == 1
    assert result[0]["name"] == "Aurora"
    assert result[0]["race"] == "Umana"


# ── nome non trovato → escluso dalla lista ────────────────────────────────────


def test_load_missing_name_excluded(monkeypatch, tmp_path, char_db):
    _, db_path = char_db
    empty_dir = tmp_path / "no_chars"
    empty_dir.mkdir()
    monkeypatch.setattr("app.db.get_db", _fake_get_db(db_path))
    monkeypatch.setattr(srv, "_CHARS_DIR", empty_dir)
    result = srv._load_char_sheets(["Fantasma"])
    assert result == []


# ── più nomi → lista multipla ─────────────────────────────────────────────────


def test_load_multiple_names(monkeypatch, char_db):
    conn, db_path = char_db
    for name in ("Alice", "Bob"):
        conn.execute(
            "INSERT INTO characters (name, card_json) VALUES (?, ?)",
            (name, json.dumps({"traits": [name.lower()]})),
        )
    conn.commit()
    monkeypatch.setattr("app.db.get_db", _fake_get_db(db_path))
    result = srv._load_char_sheets(["Alice", "Bob"])
    assert len(result) == 2
    names = [s["name"] for s in result]
    assert "Alice" in names
    assert "Bob" in names
