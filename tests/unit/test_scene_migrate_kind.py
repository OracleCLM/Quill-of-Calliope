"""
Test aggiuntivi per app/scene_migrate.py.
Focus: mapping type→kind, chars senza id/name, dir vuote, title persisted.
"""
from __future__ import annotations

import yaml

from app.db import get_db, init_schema
from app.scene_migrate import migrate_all, migrate_scene_yaml


def _init(tmp_path):
    db = str(tmp_path / "t.db")
    init_schema(get_db(db))
    return db


def _write_yaml(path, data):
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


# ── migrate_scene_yaml ────────────────────────────────────────────────────────

def test_migrate_scene_yaml_stores_title(tmp_path):
    db = _init(tmp_path)
    f = tmp_path / "s.yaml"
    _write_yaml(f, {"scene_id": "s01", "title": "La vigilia della battaglia"})
    migrate_scene_yaml(str(f), db_path=db)
    row = get_db(db).execute("SELECT title FROM scenes WHERE id='s01'").fetchone()
    assert row is not None
    assert row[0] == "La vigilia della battaglia"


# ── migrate_all — kind mapping ────────────────────────────────────────────────

def test_migrate_all_pc_type_becomes_player(tmp_path):
    scenes = tmp_path / "scenes"
    chars = tmp_path / "chars"
    scenes.mkdir()
    chars.mkdir()
    _write_yaml(chars / "aurora.yaml", {"id": "aurora", "name": "Aurora", "type": "pc"})
    db = _init(tmp_path)
    migrate_all(str(scenes), str(chars), db_path=db)
    row = get_db(db).execute("SELECT kind FROM characters WHERE id='aurora'").fetchone()
    assert row is not None and row[0] == "player"


def test_migrate_all_npc_type_becomes_npc(tmp_path):
    scenes = tmp_path / "scenes"
    chars = tmp_path / "chars"
    scenes.mkdir()
    chars.mkdir()
    _write_yaml(chars / "boss.yaml", {"id": "boss", "name": "Il Drago", "type": "npc"})
    db = _init(tmp_path)
    migrate_all(str(scenes), str(chars), db_path=db)
    row = get_db(db).execute("SELECT kind FROM characters WHERE id='boss'").fetchone()
    assert row is not None and row[0] == "npc"


def test_migrate_all_missing_type_defaults_to_npc(tmp_path):
    scenes = tmp_path / "scenes"
    chars = tmp_path / "chars"
    scenes.mkdir()
    chars.mkdir()
    _write_yaml(chars / "anon.yaml", {"id": "anon-01", "name": "Anonimo"})
    db = _init(tmp_path)
    migrate_all(str(scenes), str(chars), db_path=db)
    row = get_db(db).execute("SELECT kind FROM characters WHERE id='anon-01'").fetchone()
    assert row is not None and row[0] == "npc"


# ── migrate_all — char senza id/name ─────────────────────────────────────────

def test_migrate_all_char_without_id_is_skipped(tmp_path):
    scenes = tmp_path / "scenes"
    chars = tmp_path / "chars"
    scenes.mkdir()
    chars.mkdir()
    _write_yaml(chars / "noname.yaml", {"name": "Nessun ID"})
    db = _init(tmp_path)
    result = migrate_all(str(scenes), str(chars), db_path=db)
    assert result["characters"] == 0
    count = get_db(db).execute("SELECT COUNT(*) FROM characters").fetchone()[0]
    assert count == 0


def test_migrate_all_char_without_name_is_skipped(tmp_path):
    scenes = tmp_path / "scenes"
    chars = tmp_path / "chars"
    scenes.mkdir()
    chars.mkdir()
    _write_yaml(chars / "noid.yaml", {"id": "noid-01"})
    db = _init(tmp_path)
    result = migrate_all(str(scenes), str(chars), db_path=db)
    assert result["characters"] == 0


# ── migrate_all — dir vuote ───────────────────────────────────────────────────

def test_migrate_all_empty_dirs(tmp_path):
    scenes = tmp_path / "scenes"
    chars = tmp_path / "chars"
    scenes.mkdir()
    chars.mkdir()
    db = _init(tmp_path)
    result = migrate_all(str(scenes), str(chars), db_path=db)
    assert result == {"scenes": 0, "characters": 0, "skipped": []}
