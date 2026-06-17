"""GAP-3: resolver-schede canonico (YAML -> character_sheets -> name-only) + enrichment."""

import os
import tempfile

import yaml

from app.calliope_shell import characters_service as cs
from app.calliope_shell.scene_retrieval import retrieve_scene_sheets
from app.db import get_db, init_schema, new_id
from app.db.characters import add_character_to_scene


def _write_draft(d, stem, data):
    with open(os.path.join(d, f"{stem}.draft.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True)


def test_resolver_prefers_yaml(monkeypatch):
    d = tempfile.mkdtemp(prefix="chars-")
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", d)
    _write_draft(d, "testhero", {"name": "TestHero", "backstory": "Storia del nord.",
                                 "personality": "brave, loyal"})
    s = cs.resolve_character_sheet("TestHero")
    assert s["source"] == "yaml"
    assert "Storia del nord." in s["backstory"]
    assert "brave" in s["traits"]


def test_resolver_falls_back_to_character_sheets(monkeypatch):
    d = tempfile.mkdtemp(prefix="chars-")
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", d)  # nessun YAML
    _fd, db = tempfile.mkstemp(suffix=".db")
    conn = get_db(db)
    init_schema(conn)
    conn.execute(
        "INSERT INTO character_sheets(id,character_name,content,position_order) VALUES(?,?,?,0)",
        (new_id(), "Bruno", "Bruno è un mercante astuto."),
    )
    conn.commit()
    s = cs.resolve_character_sheet("Bruno", conn=conn)
    conn.close()
    assert s["source"] == "character_sheets"
    assert "mercante" in s["backstory"]


def test_resolver_name_only_when_nothing(monkeypatch):
    d = tempfile.mkdtemp(prefix="chars-")
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", d)
    s = cs.resolve_character_sheet("Sconosciuto")
    assert s["source"] == "none"
    assert s["backstory"] == ""


def test_retrieve_scene_sheets_enriched_from_yaml(monkeypatch):
    """Roster char con card_json VUOTO -> retrieve_scene_sheets arricchisce dal YAML (non name-only)."""
    d = tempfile.mkdtemp(prefix="chars-")
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", d)
    _write_draft(d, "aria", {"name": "Aria", "backstory": "Cresciuta tra i ghiacci del nord.",
                             "personality": "calm, wry"})
    _fd, db = tempfile.mkstemp(suffix=".db")
    conn = get_db(db)
    init_schema(conn)
    conn.execute("INSERT INTO scenes(id,title,created_at,updated_at) "
                 "VALUES(?,?,datetime('now'),datetime('now'))", ("s1", "S"))
    cid = new_id()
    conn.execute("INSERT INTO characters(id,name,created_at,updated_at) "
                 "VALUES(?,?,datetime('now'),datetime('now'))", (cid, "Aria"))
    conn.commit()
    add_character_to_scene(conn, "s1", cid, role="protagonist")
    sheets = retrieve_scene_sheets("s1", conn)
    conn.close()
    assert len(sheets) == 1
    assert "ghiacci" in sheets[0]["backstory"], "scheda non arricchita (resta name-only)"
    assert "calm" in sheets[0]["traits"]
