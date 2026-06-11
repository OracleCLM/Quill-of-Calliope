"""Contract VG-2 (gap F2): migra i metadata scene-YAML -> DB (popola scene-list reale).

Le scene-YAML sono summary (no messaggi individuali; quelli vengono dall'import Discord/ChatGPT).
Questo migra i metadata (scene_id, title) nel DB scene-as-chat, idempotente.
"""
import yaml
from app.db import get_db, init_schema
from app.scene_migrate import migrate_scene_yaml


def _write_yaml(tmp_path, sid, title):
    p = tmp_path / f"{sid}.yaml"
    p.write_text(yaml.safe_dump({"scene_id": sid, "title": title, "status": "draft"}), encoding="utf-8")
    return p


def test_migrate_inserts_scene(tmp_path):
    db = tmp_path / "t.db"
    init_schema(get_db(db))
    y = _write_yaml(tmp_path, "scene_42", "La Battaglia")
    sid = migrate_scene_yaml(str(y), db_path=str(db))
    conn = get_db(db)
    row = conn.execute("SELECT title FROM scenes WHERE id=?", (sid,)).fetchone()
    conn.close()
    assert row is not None and row[0] == "La Battaglia"


def test_migrate_idempotent(tmp_path):
    db = tmp_path / "t.db"
    init_schema(get_db(db))
    y = _write_yaml(tmp_path, "scene_42", "La Battaglia")
    migrate_scene_yaml(str(y), db_path=str(db))
    migrate_scene_yaml(str(y), db_path=str(db))
    conn = get_db(db)
    n = conn.execute("SELECT COUNT(*) FROM scenes WHERE id='scene_42'").fetchone()[0]
    conn.close()
    assert n == 1
