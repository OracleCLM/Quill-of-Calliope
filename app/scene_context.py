"""Scene-context DB-aware per il draft-generation (chiusura gap F1, VG-1).

Sostituisce la lettura flat-YAML del draft-gen con il DB scene-as-chat: il
/api/messages/next userà build_scene_context per comporre il prompt in-contesto.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from app.db import get_db


def build_scene_context(scene_id: str, db_path: str | None = None, max_msgs: int = 100) -> str:
    """
    Ritorna il contesto-scena dal DB per il draft-gen (vedi tests/unit/test_scene_context_db.py):
      - "Scene: <titolo>" + gli ultimi max_msgs messaggi ordinati come "<author>: <content>"
      - scena inesistente -> "" (stringa vuota)
    max_msgs=0 carica tutti (admin/debug). Default: 100.
    """
    db = get_db(db_path)

    row = db.execute("SELECT title FROM scenes WHERE id = ?", (scene_id,)).fetchone()
    if row is None:
        return ""
    title = row[0]

    if max_msgs > 0:
        rows = db.execute(
            "SELECT author_name, content_original FROM messages "
            "WHERE scene_id = ? ORDER BY position_order DESC LIMIT ?",
            (scene_id, max_msgs),
        ).fetchall()
        rows = list(reversed(rows))
    else:
        rows = db.execute(
            "SELECT author_name, content_original FROM messages "
            "WHERE scene_id = ? ORDER BY position_order",
            (scene_id,),
        ).fetchall()

    lines = [f"Scene: {title}"]
    for author_name, content_original in rows:
        lines.append(f"{author_name}: {content_original}")

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
    # DB-FIRST: path canonico scene-as-chat.
    ctx = build_scene_context(scene_id, db_path)
    if ctx:
        return ctx

    # FALLBACK-YAML: scena solo come *.yaml (compat retro durante la migrazione).
    if scenes_dir is not None:
        sdir = Path(scenes_dir)
        if sdir.is_dir():
            for yfile in sorted(sdir.glob("*.yaml")):
                if scene_id in yfile.stem:
                    data = yaml.safe_load(yfile.read_text(encoding="utf-8")) or {}
                    title = data.get("title", "")
                    summary = data.get("summary", "")
                    participants = data.get("participants", []) or []
                    return (
                        f"Scene: {title}\n"
                        f"Summary: {summary}\n"
                        f"Participants: {', '.join(participants)}"
                    )

    # VUOTO: né DB né YAML.
    return ""
