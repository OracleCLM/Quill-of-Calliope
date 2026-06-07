"""
Modulo di gestione della Lore knowledge-base per il database di Calliope.

Fornisce funzioni CRUD per la tabella ``lore_entries`` e gestisce le
associazioni con gli archi narrativi tramite ``arc_lore``.
"""

from __future__ import annotations

import sqlite3
from typing import List, Mapping, Optional

# Importiamo utility generiche dal package ``app.db``.
try:
    from app.db import new_id  # type: ignore
except Exception:  # pragma: no cover
    # Fallback se new_id non è disponibile (non dovrebbe succedere)
    new_id = None  # type: ignore


def _row_to_dict(cursor: sqlite3.Cursor, row: tuple) -> dict:
    """Converte una riga del cursore in un dizionario."""
    cols = [desc[0] for desc in cursor.description]
    return dict(zip(cols, row))


def add_lore_entry(
    conn: sqlite3.Connection,
    *,
    title: str,
    category: str = "other",
    content_text: Optional[str] = None,
    created_by: str = "operator",
) -> str:
    """
    Inserisce una nuova voce nella lore.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    title:
        Titolo della voce.
    category:
        Categoria della voce (deve essere valida secondo lo schema).
    content_text:
        Contenuto testuale della voce.
    created_by:
        Autore della voce.

    Returns
    -------
    str
        L'ID della voce appena inserita.
    """
    if not title:
        raise ValueError("title non può essere vuoto")
    if len(title) > 255:
        raise ValueError("title non può superare 255 caratteri")
    if new_id is None:
        raise RuntimeError("new_id function not available")

    entry_id = new_id()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO lore_entries
            (id, title, category, content_text, created_by)
        VALUES (?, ?, ?, ?, ?)
        """,
        (entry_id, title, category, content_text, created_by),
    )
    conn.commit()
    return entry_id


def get_lore_entry(
    conn: sqlite3.Connection,
    entry_id: str,
) -> Optional[Mapping[str, object]]:
    """
    Recupera una singola voce della lore per ID.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    entry_id:
        ID della voce da recuperare.

    Returns
    -------
    Optional[Mapping[str, object]]
        Dizionario con i dati della voce o None se non trovata.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM lore_entries WHERE id = ?",
        (entry_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_dict(cur, row)


def list_lore_entries(
    conn: sqlite3.Connection,
    category: Optional[str] = None,
) -> List[Mapping[str, object]]:
    """
    Elenca le voci della lore, opzionalmente filtrate per categoria.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    category:
        Se fornito, filtra solo questa categoria.

    Returns
    -------
    List[Mapping[str, object]]
        Lista di dizionari rappresentanti le voci.
    """
    cur = conn.cursor()
    if category:
        cur.execute(
            "SELECT * FROM lore_entries WHERE category = ?",
            (category,),
        )
    else:
        cur.execute("SELECT * FROM lore_entries")

    rows = cur.fetchall()
    return [_row_to_dict(cur, row) for row in rows]


def update_lore_entry(
    conn: sqlite3.Connection,
    entry_id: str,
    *,
    title: Optional[str] = None,
    content_text: Optional[str] = None,
    category: Optional[str] = None,
) -> bool:
    """
    Aggiorna una voce della lore.

    Aggiorna solo i campi forniti (non None).

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    entry_id:
        ID della voce da aggiornare.
    title:
        Nuovo titolo.
    content_text:
        Nuovo contenuto.
    category:
        Nuova categoria.

    Returns
    -------
    bool
        True se la voce esisteva ed è stata aggiornata, False altrimenti.
    """
    # Verifichiamo prima l'esistenza della riga
    check_cur = conn.cursor()
    check_cur.execute("SELECT 1 FROM lore_entries WHERE id = ?", (entry_id,))
    exists = check_cur.fetchone() is not None

    if not exists:
        return False

    # Costruiamo dinamicamente la query di aggiornamento
    updates = []
    params = []
    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if content_text is not None:
        updates.append("content_text = ?")
        params.append(content_text)
    if category is not None:
        updates.append("category = ?")
        params.append(category)

    if not updates:
        # Nessun campo da aggiornare, ma la riga esiste
        return True

    params.append(entry_id)
    query = f"UPDATE lore_entries SET {', '.join(updates)} WHERE id = ?"

    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    return True


def delete_lore_entry(
    conn: sqlite3.Connection,
    entry_id: str,
) -> bool:
    """
    Elimina una voce della lore.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    entry_id:
        ID della voce da eliminare.

    Returns
    -------
    bool
        True se eliminata, False se non esisteva.
    """
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM lore_entries WHERE id = ?",
        (entry_id,),
    )
    conn.commit()
    return cur.rowcount > 0


def link_lore_to_arc(
    conn: sqlite3.Connection,
    arc_id: str,
    entry_id: str,
) -> None:
    """
    Associa una voce della lore a un arco narrativo.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    arc_id:
        ID dell'arco.
    entry_id:
        ID della voce della lore.
    """
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO arc_lore (arc_id, lore_entry_id) VALUES (?, ?)",
        (arc_id, entry_id),
    )
    conn.commit()


def list_lore_for_arc(
    conn: sqlite3.Connection,
    arc_id: str,
) -> List[Mapping[str, object]]:
    """
    Recupera tutte le voci della lore associate a un arco.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    arc_id:
        ID dell'arco.

    Returns
    -------
    List[Mapping[str, object]]
        Lista di dizionari rappresentanti le voci collegate.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT le.*
        FROM lore_entries le
        JOIN arc_lore al ON le.id = al.lore_entry_id
        WHERE al.arc_id = ?
        """,
        (arc_id,),
    )
    rows = cur.fetchall()
    return [_row_to_dict(cur, row) for row in rows]
