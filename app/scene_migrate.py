"""Migrazione metadata scene-YAML -> DB scene-as-chat (chiusura gap F2, VG-2)."""
from __future__ import annotations


def migrate_scene_yaml(yaml_path: str, db_path: str | None = None) -> str:
    """
    Legge una scene-YAML (scene_id, title) e inserisce la scena nel DB, idempotente
    (se l'id esiste gia', non duplica). Ritorna lo scene_id.
    Vedi tests/unit/test_scene_migrate.py. Usa yaml.safe_load + app.db.get_db.
    """
    raise NotImplementedError("VG-2: implementazione aider")


def migrate_all(scenes_dir: str, chars_dir: str, db_path: str | None = None) -> dict:
    """
    Migrazione BATCH idempotente di tutti gli YAML reali -> DB (chiusura REALE F2, VG-2b).

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
    raise NotImplementedError("VG-2b: implementazione aider (batch migrate_all)")
