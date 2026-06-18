"""
Modulo CRUD per la tabella ``arcs`` (archi narrativi) di Calliope.

Fornisce le funzioni usate dalle route ``arcs_db_routes`` per creare,
elencare, leggere ed eliminare archi, e per elencare le scene associate a
un arco tramite la colonna ``scenes.arc_id``.
"""

from __future__ import annotations

import sqlite3
from typing import List, Mapping, Optional

from app.db import new_id


def create_arc(conn: sqlite3.Connection, title: str, description: str = "") -> str:
    """Inserisce un nuovo arco e ne ritorna l'id UUID.

    Raise ``ValueError`` se ``title`` è vuoto.
    """
    if not title:
        raise ValueError("title is required")
    arc_id = new_id()
    conn.execute(
        "INSERT INTO arcs (id, title, description) VALUES (?, ?, ?)",
        (arc_id, title, description),
    )
    conn.commit()
    return arc_id


def list_arcs(conn: sqlite3.Connection) -> List[Mapping[str, object]]:
    """Ritorna tutti gli archi come dizionari, ordinati per ``created_at`` DESC."""
    rows = conn.execute("SELECT * FROM arcs ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_arc(conn: sqlite3.Connection, arc_id: str) -> Optional[dict]:
    """Ritorna il dizionario dell'arco, o ``None`` se non esiste."""
    row = conn.execute("SELECT * FROM arcs WHERE id = ?", (arc_id,)).fetchone()
    return dict(row) if row is not None else None


def delete_arc(conn: sqlite3.Connection, arc_id: str) -> bool:
    """Elimina l'arco; ritorna ``True`` se eliminato, ``False`` se non esisteva."""
    cur = conn.execute("DELETE FROM arcs WHERE id = ?", (arc_id,))
    conn.commit()
    return cur.rowcount > 0


def list_scenes_for_arc(
    conn: sqlite3.Connection, arc_id: str
) -> List[Mapping[str, object]]:
    """Ritorna le scene con ``arc_id`` corrispondente (lista vuota se nessuna).

    Non lancia eccezioni se ``arc_id`` non esiste: ritorna semplicemente [].
    """
    rows = conn.execute(
        "SELECT * FROM scenes WHERE arc_id = ?", (arc_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def update_arc(
    conn: sqlite3.Connection, arc_id: str, **fields: str
) -> bool:
    """Aggiorna i campi ``title`` e/o ``description`` di un arco.

    Restituisce ``True`` se l'arco è stato aggiornato, ``False`` se l'arco
    non esiste. Ignora eventuali chiavi non riconosciute.
    """
    allowed = {"title", "description"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        # nessun campo aggiornabile fornito
        return False

    # Verifica che l'arco esista
    cur = conn.execute("SELECT 1 FROM arcs WHERE id = ?", (arc_id,))
    if cur.fetchone() is None:
        return False

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    params = list(updates.values()) + [arc_id]
    conn.execute(f"UPDATE arcs SET {set_clause} WHERE id = ?", params)
    conn.commit()
    return True
