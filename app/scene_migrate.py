"""Migrazione metadata scene-YAML -> DB scene-as-chat (chiusura gap F2, VG-2)."""
from __future__ import annotations


def migrate_scene_yaml(yaml_path: str, db_path: str | None = None) -> str:
    """
    Legge una scene-YAML (scene_id, title) e inserisce la scena nel DB, idempotente
    (se l'id esiste gia', non duplica). Ritorna lo scene_id.
    Vedi tests/unit/test_scene_migrate.py. Usa yaml.safe_load + app.db.get_db.
    """
    raise NotImplementedError("VG-2: implementazione aider")
