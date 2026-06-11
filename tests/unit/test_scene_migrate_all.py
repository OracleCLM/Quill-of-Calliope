"""Contract test VG-2b (gap-review F2, chiusura REALE): migrazione BATCH YAML->DB.

VG-2 ha dato il primitivo `migrate_scene_yaml` (1 scena). MA il gap F2 reale è che
NESSUN dato RP è nel DB: 332 scene (scenes/*.yaml) + 122 char (characters/**/*.yaml)
vivono solo come flat-YAML. `migrate_all` fa il batch idempotente di tutto.

Idempotenza KEY: char inseriti con l'`id` dello YAML (es. "yan-qing"), NON via
add_character (che conia un id nuovo → duplicherebbe a ogni re-run).
"""
import yaml

from app.db import get_db, init_schema
from app.scene_migrate import migrate_all


def _seed_yaml_dirs(tmp_path):
    scenes = tmp_path / "scenes"
    chars = tmp_path / "characters"
    scenes.mkdir()
    chars.mkdir()
    (scenes / "scene_003.draft.yaml").write_text(
        yaml.safe_dump({"scene_id": "scene_003", "title": "Kikyo Leaves the Shrine"}), encoding="utf-8"
    )
    (scenes / "scene_004.draft.yaml").write_text(
        yaml.safe_dump({"scene_id": "scene_004", "title": "The Tavern Brawl"}), encoding="utf-8"
    )
    (chars / "yan-qing.draft.yaml").write_text(
        yaml.safe_dump({"id": "yan-qing", "name": "Yan Qing", "type": "pc"}), encoding="utf-8"
    )
    (chars / "narrator.canon.yaml").write_text(
        yaml.safe_dump({"id": "narrator", "name": "NARRATOR", "type": "npc"}), encoding="utf-8"
    )
    return scenes, chars


def _counts(db_path):
    conn = get_db(db_path)
    s = conn.execute("SELECT COUNT(*) FROM scenes").fetchone()[0]
    c = conn.execute("SELECT COUNT(*) FROM characters").fetchone()[0]
    conn.close()
    return s, c


def test_migrate_all_inserts_scenes_and_chars(tmp_path):
    scenes, chars = _seed_yaml_dirs(tmp_path)
    db = str(tmp_path / "t.db")
    init_schema(get_db(db))
    res = migrate_all(str(scenes), str(chars), db_path=db)
    assert res["scenes"] == 2
    assert res["characters"] == 2
    assert _counts(db) == (2, 2)


def test_migrate_all_idempotent(tmp_path):
    scenes, chars = _seed_yaml_dirs(tmp_path)
    db = str(tmp_path / "t.db")
    init_schema(get_db(db))
    migrate_all(str(scenes), str(chars), db_path=db)
    migrate_all(str(scenes), str(chars), db_path=db)  # re-run: nessun duplicato
    assert _counts(db) == (2, 2)


def test_migrate_all_char_uses_yaml_id(tmp_path):
    scenes, chars = _seed_yaml_dirs(tmp_path)
    db = str(tmp_path / "t.db")
    init_schema(get_db(db))
    migrate_all(str(scenes), str(chars), db_path=db)
    conn = get_db(db)
    row = conn.execute("SELECT name FROM characters WHERE id = ?", ("yan-qing",)).fetchone()
    conn.close()
    assert row is not None and row[0] == "Yan Qing"
