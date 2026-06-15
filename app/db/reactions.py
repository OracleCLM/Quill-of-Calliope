"""
Gestione reazioni per Calliope — allineato alla migration 002_scene_reactions.sql.

Schema canonico (migration 002):
    scene_reactions (id TEXT PK, message_id TEXT, character_id TEXT, emoji TEXT, created_at TEXT)
"""

from __future__ import annotations

import sqlite3
from typing import List, Mapping

from app.db import new_id


def add_reaction(
    conn: sqlite3.Connection,
    *,
    message_id: str,
    character_id: str,
    emoji: str = "",
) -> str:
    """
    Inserisce una reazione in scene_reactions. Restituisce l'id TEXT generato.
    """
    reaction_id = new_id()
    conn.execute(
        "INSERT INTO scene_reactions (id, message_id, character_id, emoji) VALUES (?, ?, ?, ?)",
        (reaction_id, message_id, character_id, emoji),
    )
    conn.commit()
    return reaction_id


def list_reactions(
    conn: sqlite3.Connection,
    *,
    message_id: str,
) -> List[Mapping[str, object]]:
    """
    Restituisce le reazioni per message_id ordinate per created_at.
    """
    cur = conn.execute(
        "SELECT * FROM scene_reactions WHERE message_id = ? ORDER BY created_at",
        (message_id,),
    )
    col_names = [desc[0] for desc in cur.description]
    return [dict(zip(col_names, row)) for row in cur.fetchall()]
