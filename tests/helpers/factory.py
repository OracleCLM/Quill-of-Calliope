"""Factory di parent-row riutilizzabili per i test (schema reale, raw sqlite3).

Sblocca il setup multi-FK: i test non devono ricostruire ogni volta le righe
parent valide con i NOT NULL/CHECK corretti. Lavora sul VERO schema applicato
via ``app.db.init_schema`` — nessun create-table proprio, nessun ORM.

Ordine FK: scene -> character -> message.
"""

from __future__ import annotations

import sqlite3

from app.db import new_id


def make_scene(conn: sqlite3.Connection, *, title: str = "Test Scene", **kw) -> str:
    """Inserisce una scena valida (scenes.title NOT NULL) e ritorna il suo id."""
    sid = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (sid, title))
    conn.commit()
    return sid


def make_character(
    conn: sqlite3.Connection, *, name: str = "Test Char", kind: str = "npc", **kw
) -> str:
    """Inserisce un character valido (name NOT NULL, kind CHECK) e ritorna l'id."""
    cid = new_id()
    conn.execute(
        "INSERT INTO characters (id, name, kind) VALUES (?, ?, ?)",
        (cid, name, kind),
    )
    conn.commit()
    return cid


def make_message(
    conn: sqlite3.Connection,
    scene_id: str,
    *,
    character_id: str | None = None,
    ts: str = "2026-01-01T00:00:00Z",
    content_original: str = "hi",
    position_order: int = 0,
    source: str = "manual",
    **kw,
) -> str:
    """Inserisce un message valido (id, scene_id, ts NOT NULL) e ritorna l'id."""
    mid = new_id()
    conn.execute(
        "INSERT INTO messages "
        "(id, scene_id, character_id, content_original, ts, source, position_order) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (mid, scene_id, character_id, content_original, ts, source, position_order),
    )
    conn.commit()
    return mid
