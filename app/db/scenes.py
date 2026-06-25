"""DB helper per la risorsa scene.

Creato come modulo dedicato (WI-35 list_scenes, WI-38 assign_scene_to_arc):
le route in ``app/calliope_shell/scenes_db_routes.py`` delegano qui invece di
incorporare SQL inline, allineandosi al pattern degli altri ``app/db/*`` moduli.
"""

from __future__ import annotations

import sqlite3
from typing import List, Optional

# Colonne esposte dall'elenco scene (coerenti con la route GET /api/db/scenes).
_SCENE_COLS = (
    "s.id, s.title, s.arc_id, s.location, s.is_readonly, "
    "s.last_activity_at, s.updated_at, "
    "COUNT(m.id) AS message_count"
)
_SCENE_FROM = "FROM scenes s LEFT JOIN messages m ON m.scene_id = s.id"
_SCENE_GROUP = " GROUP BY s.id"
_SCENE_ORDER = " ORDER BY COALESCE(s.last_activity_at, s.updated_at) DESC"


def list_scenes(
    conn: sqlite3.Connection,
    title_contains: Optional[str] = None,
) -> List[dict]:
    """
    Elenca le scene, opzionalmente filtrate per sottostringa del titolo.

    Il filtro usa ``LIKE '%...%'`` (case-insensitive su ASCII, default SQLite).
    Senza ``title_contains`` ritorna tutte le scene.
    Ogni riga include ``message_count`` e ``is_readonly``.
    """
    base = f"SELECT {_SCENE_COLS} {_SCENE_FROM}"
    if title_contains is not None:
        cur = conn.execute(
            base + " WHERE s.title LIKE ?" + _SCENE_GROUP + _SCENE_ORDER,
            (f"%{title_contains}%",),
        )
    else:
        cur = conn.execute(base + _SCENE_GROUP + _SCENE_ORDER)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def assign_scene_to_arc(
    conn: sqlite3.Connection,
    scene_id: str,
    arc_id: Optional[str],
) -> bool:
    """
    Assegna l'arco a una scena (``arc_id=None`` rimuove l'associazione).

    Ritorna True se la scena esiste ed è stata aggiornata, False altrimenti.
    """
    cur = conn.execute(
        "UPDATE scenes SET arc_id = ? WHERE id = ?",
        (arc_id, scene_id),
    )
    conn.commit()
    return cur.rowcount > 0
