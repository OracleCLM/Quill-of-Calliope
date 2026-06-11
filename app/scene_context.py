"""Scene-context DB-aware per il draft-generation (chiusura gap F1, VG-1).

Sostituisce la lettura flat-YAML del draft-gen con il DB scene-as-chat: il
/api/messages/next userà build_scene_context per comporre il prompt in-contesto.
"""
from __future__ import annotations


def build_scene_context(scene_id: str, db_path: str | None = None) -> str:
    """
    Ritorna il contesto-scena dal DB per il draft-gen (vedi tests/unit/test_scene_context_db.py):
      - "Scene: <titolo>" + gli ultimi messaggi ordinati come "<author>: <content>"
      - scena inesistente -> "" (stringa vuota)
    Usa app.db.get_db(db_path) + app.db.messages.get_scene_message_page / list_messages_for_scene.
    """
    raise NotImplementedError("VG-1: implementazione aider")
