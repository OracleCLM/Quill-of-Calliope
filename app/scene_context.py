"""Scene-context DB-aware per il draft-generation (chiusura gap F1, VG-1).

Sostituisce la lettura flat-YAML del draft-gen con il DB scene-as-chat: il
/api/messages/next userà build_scene_context per comporre il prompt in-contesto.
"""
from __future__ import annotations

from pathlib import Path

from app.db import get_db
from app.db.messages import list_messages_for_scene


def build_scene_context(scene_id: str, db_path: str | None = None) -> str:
    """
    Ritorna il contesto-scena dal DB per il draft-gen (vedi tests/unit/test_scene_context_db.py):
      - "Scene: <titolo>" + gli ultimi messaggi ordinati come "<author>: <content>"
      - scena inesistente -> "" (stringa vuota)
    Usa app.db.get_db(db_path) + app.db.messages.get_scene_message_page / list_messages_for_scene.
    """
    db = get_db(db_path)

    # Recupera il titolo della scena per verificare l'esistenza
    row = db.execute("SELECT title FROM scenes WHERE id = ?", (scene_id,)).fetchone()
    if row is None:
        return ""
    title = row[0]

    # Recupera i messaggi
    messages = list_messages_for_scene(db, scene_id)

    # Ordina i messaggi per position_order come richiesto
    messages.sort(key=lambda m: m["position_order"])

    # Costruisce la stringa di output
    lines = [f"Scene: {title}"]
    for msg in messages:
        lines.append(f"{msg['author_name']}: {msg['content_original']}")

    return "\n".join(lines)


def resolve_scene_context(
    scene_id: str,
    db_path: str | None = None,
    scenes_dir: Path | None = None,
) -> str:
    """
    Risolve il contesto-scena per il draft-gen DB-FIRST con fallback flat-YAML (VG-1b).

    Contratto (vedi tests/unit/test_scene_context_resolve.py) — chiude il FATALE F1:
      - DB-FIRST: se la scena esiste nel DB → ritorna build_scene_context(scene_id, db_path)
        (titolo + messaggi). È il path canonico scene-as-chat.
      - FALLBACK-YAML: se non è nel DB ma esiste un *.yaml in scenes_dir il cui stem
        contiene scene_id → ritorna un contesto flat-YAML:
        "Scene: <title>\\nSummary: <summary>\\nParticipants: <p1, p2>"
        (compat retro durante la migrazione). Usa yaml.safe_load.
      - VUOTO: né DB né YAML → "".

    Le route /api/messages/next e /api/messages/continue DEVONO usare questo helper
    al posto del glob _SCENES_DIR inline.
    """
    raise NotImplementedError("VG-1b: implementare resolve_scene_context (DB-first + YAML-fallback)")
