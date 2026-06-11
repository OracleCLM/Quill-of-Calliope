"""Migrazione metadata scene-YAML -> DB scene-as-chat (chiusura gap F2, VG-2)."""
from __future__ import annotations

import yaml
from pathlib import Path

from app.db import get_db


def migrate_scene_yaml(yaml_path: str, db_path: str | None = None) -> str:
    """
    Legge una scene-YAML (scene_id, title) e inserisce la scena nel DB,
    idempotente (se l'id esiste gia', non duplica). Ritorna lo scene_id.
    Vedi tests/unit/test_scene_migrate.py. Usa yaml.safe_load + app.db.get_db.
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    scene_id = data.get("scene_id")
    title = data.get("title")

    db = get_db(db_path)

    cursor = db.execute("SELECT id FROM scenes WHERE id = ?", (scene_id,))
    if cursor.fetchone() is None:
        db.execute(
            "INSERT INTO scenes (id, title) VALUES (?, ?)",
            (scene_id, title),
        )
        db.commit()

    return scene_id


def migrate_all(scenes_dir: str, chars_dir: str, db_path: str | None = None) -> dict:
    """
    Migrazione BATCH idempotente di tutti gli YAML reali -> DB
    (chiusura REALE F2, VG-2b).

    Contratto (vedi tests/unit/test_scene_migrate_all.py):
      - SCENE: per ogni file in Path(scenes_dir).glob("*.yaml") chiama
        migrate_scene_yaml(path, db_path) (riusa il primitivo, idempotente su scene_id).
      - CHAR: per ogni file in Path(chars_dir).rglob("*.yaml"): yaml.safe_load → leggi
        id + name (+ type). INSERT diretto in characters usando l'`id` DELLO YAML
        (NON add_character, che conia un id nuovo): se una riga con quell'id NON esiste,
        inserisci (id, name, kind) con kind='player' se type=='pc' altrimenti 'npc';
        se esiste, salta (idempotente).
      - Ritorna {"scenes": n_scene_processate, "characters": n_char_processati}.
    """
    skipped = []
    scenes_count = 0
    for p in sorted(Path(scenes_dir).glob("*.yaml")):
        try:
            migrate_scene_yaml(str(p), db_path)
            scenes_count += 1
        except Exception:
            skipped.append(str(p))

    chars_count = 0
    for p in sorted(Path(chars_dir).rglob("*.yaml")):
        try:
            data = yaml.safe_load(p.read_text())
            cid = data.get("id")
            name = data.get("name")
            if not cid or not name:
                continue

            db = get_db(db_path)
            cursor = db.execute("SELECT 1 FROM characters WHERE id = ?", (cid,))
            if cursor.fetchone() is None:
                kind = "player" if data.get("type") == "pc" else "npc"
                db.execute(
                    "INSERT INTO characters (id, name, kind) VALUES (?, ?, ?)",
                    (cid, name, kind),
                )
                db.commit()
                chars_count += 1
        except Exception:
            skipped.append(str(p))

    return {"scenes": scenes_count, "characters": chars_count, "skipped": skipped}
