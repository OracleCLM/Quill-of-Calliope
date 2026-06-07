"""
Modulo di gestione dei messaggi per il database di Calliope.

Fornisce funzioni CRUD per la tabella ``messages`` e gestisce le
associazioni con scene e personaggi.
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


def add_message(
    conn: sqlite3.Connection,
    *,
    scene_id: str,
    character_id: Optional[str] = None,
    author_name: str,
    content_original: str,
    content_enhanced: Optional[str] = None,
    source: str = "manual",
    position_order: int = 0,
    is_summary: int = 0,
) -> str:
    """
    Inserisce un nuovo messaggio nella tabella messages.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    scene_id:
        ID della scena a cui il messaggio appartiene.
    character_id:
        ID del personaggio che ha inviato il messaggio (opzionale).
    author_name:
        Nome dell'autore del messaggio.
    content_original:
        Contenuto originale del messaggio.
    content_enhanced:
        Contenuto enhanced/processato del messaggio (opzionale).
    source:
        Fonte del messaggio (default: 'manual').
    position_order:
        Ordine di posizione nella scena (default: 0).
    is_summary:
        Flag indicante se il messaggio è un riassunto (default: 0).

    Returns
    -------
    str
        L'ID del messaggio appena inserito.
    """
    if new_id is None:
        raise RuntimeError("new_id function not available")

    message_id = new_id()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO messages
            (id, scene_id, character_id, author_name, content_original, content_enhanced, ts, source, position_order, is_summary)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, ?)
        """,
        (message_id, scene_id, character_id, author_name, content_original, content_enhanced, source, position_order, is_summary),
    )
    conn.commit()
    return message_id


def insert_message_at(
    conn: sqlite3.Connection,
    *,
    scene_id: str,
    character_id: Optional[str] = None,
    author_name: str,
    content_original: str,
    content_enhanced: Optional[str] = None,
    source: str = "manual",
    position_order: int,
    is_summary: int = 0,
) -> str:
    """
    Inserisce un nuovo messaggio alla posizione specificata, spostando indietro i messaggi esistenti.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    scene_id:
        ID della scena a cui il messaggio appartiene.
    character_id:
        ID del personaggio che ha inviato il messaggio (opzionale).
    author_name:
        Nome dell'autore del messaggio.
    content_original:
        Contenuto originale del messaggio.
    content_enhanced:
        Contenuto enhanced/processato del messaggio (opzionale).
    source:
        Fonte del messaggio (default: 'manual').
    position_order:
        Posizione dove inserire il messaggio.
    is_summary:
        Flag indicante se il messaggio è un riassunto (default: 0).

    Returns
    -------
    str
        L'ID del messaggio appena inserito.
    """
    if new_id is None:
        raise RuntimeError("new_id function not available")

    # Prima spostiamo indietro i messaggi esistenti dalla posizione specificata
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE messages
        SET position_order = position_order + 1
        WHERE scene_id = ? AND position_order >= ?
        """,
        (scene_id, position_order),
    )

    # Poi inseriamo il nuovo messaggio
    message_id = new_id()
    cur.execute(
        """
        INSERT INTO messages
            (id, scene_id, character_id, author_name, content_original, content_enhanced, ts, source, position_order, is_summary)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, ?)
        """,
        (message_id, scene_id, character_id, author_name, content_original, content_enhanced, source, position_order, is_summary),
    )
    conn.commit()
    return message_id


def list_messages_for_scene(
    conn: sqlite3.Connection,
    scene_id: str,
) -> List[Mapping[str, object]]:
    """
    Elenca tutti i messaggi per una scena, ordinati per position_order.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    scene_id:
        ID della scena per cui recuperare i messaggi.

    Returns
    -------
    List[Mapping[str, object]]
        Lista di dizionari rappresentanti i messaggi.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM messages
        WHERE scene_id = ?
        ORDER BY position_order
        """,
        (scene_id,),
    )
    rows = cur.fetchall()
    return [_row_to_dict(cur, row) for row in rows]


def count_messages_for_scene(
    conn: sqlite3.Connection,
    scene_id: str,
) -> int:
    """
    Conta i messaggi per una scena.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    scene_id:
        ID della scena per cui contare i messaggi.

    Returns
    -------
    int
        Numero di messaggi nella scena.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) FROM messages WHERE scene_id = ?
        """,
        (scene_id,),
    )
    result = cur.fetchone()
    return result[0] if result else 0


def get_message_by_id(
    conn: sqlite3.Connection,
    message_id: str,
) -> Optional[Mapping[str, object]]:
    """
    Recupera un singolo messaggio per ID.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    message_id:
        ID del messaggio da recuperare.

    Returns
    -------
    Optional[Mapping[str, object]]
        Dizionario con i dati del messaggio o None se non trovato.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM messages WHERE id = ?",
        (message_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_dict(cur, row)


def get_scene_message_page(
    conn: sqlite3.Connection,
    scene_id: str,
    page: int = 1,
    per_page: int = 50,
) -> dict:
    """
    Recupera una pagina di messaggi per una scena.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    scene_id:
        ID della scena.
    page:
        Numero della pagina (1-based).
    per_page:
        Numero di messaggi per pagina.

    Returns
    -------
    dict
        Dizionario con i messaggi e informazioni di paginazione.
    """
    offset = (page - 1) * per_page
    cur = conn.cursor()

    # Otteniamo i messaggi della pagina
    cur.execute(
        """
        SELECT * FROM messages
        WHERE scene_id = ?
        ORDER BY position_order
        LIMIT ? OFFSET ?
        """,
        (scene_id, per_page, offset),
    )
    rows = cur.fetchall()
    messages = [_row_to_dict(cur, row) for row in rows]

    # Otteniamo il totale per il calcolo delle pagine
    cur.execute(
        "SELECT COUNT(*) FROM messages WHERE scene_id = ?",
        (scene_id,),
    )
    total_result = cur.fetchone()
    total = total_result[0] if total_result else 0

    return {
        "messages": messages,
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": (total + per_page - 1) // per_page if per_page > 0 else 0,
    }


def delete_message(
    conn: sqlite3.Connection,
    message_id: str,
) -> bool:
    """
    Elimina un messaggio per ID.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    message_id:
        ID del messaggio da eliminare.

    Returns
    -------
    bool
        True se eliminato, False se non esisteva.
    """
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM messages WHERE id = ?",
        (message_id,),
    )
    conn.commit()
    return cur.rowcount > 0


def move_message(
    conn: sqlite3.Connection,
    message_id: str,
    new_position: int,
) -> bool:
    """
    Sposta un messaggio a una nuova posizione, adjustando gli altri messaggi di conseguenza.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    message_id:
        ID del messaggio da spostare.
    new_position:
        Nuova posizione per il messaggio.

    Returns
    -------
    bool
        True se lo spostamento è avvenuto con successo, False se il messaggio non esiste.
    """
    # Prima recuperiamo il messaggio per conoscere la sua scena e posizione attuale
    cur = conn.cursor()
    cur.execute(
        "SELECT scene_id, position_order FROM messages WHERE id = ?",
        (message_id,),
    )
    row = cur.fetchone()
    if row is None:
        return False

    scene_id, old_position = row

    if old_position == new_position:
        # Nessun movimento necessario
        return True

    if new_position < old_position:
        # Spostamento verso l'alto: spostiamo indietro i messaggi tra new_position e old_position-1
        cur.execute(
            """
            UPDATE messages
            SET position_order = position_order + 1
            WHERE scene_id = ? AND position_order >= ? AND position_order < ?
            """,
            (scene_id, new_position, old_position),
        )
    else:
        # Spostamento verso il basso: spostiamo avanti i messaggi tra old_position+1 e new_position
        cur.execute(
            """
            UPDATE messages
            SET position_order = position_order - 1
            WHERE scene_id = ? AND position_order > ? AND position_order <= ?
            """,
            (scene_id, old_position, new_position),
        )

    # Aggiorniamo la posizione del messaggio spostato
    cur.execute(
        "UPDATE messages SET position_order = ? WHERE id = ?",
        (new_position, message_id),
    )
    conn.commit()
    return True


def compact_scene_positions(
    conn: sqlite3.Connection,
    scene_id: str,
) -> int:
    """
    Riorganizza le position_order di una scena per eliminare gap e assicurare sequenza continua da 0.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    scene_id:
        ID della scena da compactare.

    Returns
    -------
    int
        Numero di messaggi nella scena dopo il compacting.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id FROM messages
        WHERE scene_id = ?
        ORDER BY position_order
        """,
        (scene_id,),
    )
    rows = cur.fetchall()

    # Aggiorniamo le position_order per essere sequenziali da 1
    for new_pos, (message_id,) in enumerate(rows, start=1):
        cur.execute(
            "UPDATE messages SET position_order = ? WHERE id = ?",
            (new_pos, message_id),
        )

    conn.commit()
    return len(rows)


def move_message_to_scene(
    conn: sqlite3.Connection,
    message_id: str,
    target_scene_id: str,
    new_position: int,
) -> bool:
    """
    Sposta un messaggio da una scena all'altra, adjustando le position_order di conseguenza.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    message_id:
        ID del messaggio da spostare.
    target_scene_id:
        ID della scena di destinazione.
    new_position:
        Nuova posizione nella scena di destinazione.

    Returns
    -------
    bool
        True se lo spostamento è avvenuto con successo, False se il messaggio non esiste.
    """
    # Recuperiamo il messaggio per conoscere la scena sorgente
    cur = conn.cursor()
    cur.execute(
        "SELECT scene_id FROM messages WHERE id = ?",
        (message_id,),
    )
    row = cur.fetchone()
    if row is None:
        return False

    source_scene_id = row[0]

    # Se la scena è la stessa, usiamo semplicemente move_message
    if source_scene_id == target_scene_id:
        return move_message(conn, message_id, new_position)

    # Altrimenti, dobbiamo:
    # 1. Rimuovere il messaggio dalla scena sorgente (shift indietro i successivi)
    # 2. Inserirlo nella scena destinazione alla posizione specificata (shift avanti i successivi)

    # Passo 1: Ottieniamo la posizione corrente e rimuoviamo dalla scena sorgente
    cur.execute(
        "SELECT position_order FROM messages WHERE id = ?",
        (message_id,),
    )
    pos_row = cur.fetchone()
    if pos_row is None:
        return False

    old_position = pos_row[0]

    # Shift indietro i messaggi nella scena sorgente dopo la posizione del messaggio
    cur.execute(
        """
        UPDATE messages
        SET position_order = position_order - 1
        WHERE scene_id = ? AND position_order > ?
        """,
        (source_scene_id, old_position),
    )

    # Passo 2: Shift avanti i messaggi nella scena destinazione dalla nuova posizione
    cur.execute(
        """
        UPDATE messages
        SET position_order = position_order + 1
        WHERE scene_id = ? AND position_order >= ?
        """,
        (target_scene_id, new_position),
    )

    # Passo 3: Aggiorniamo scena e posizione del messaggio
    cur.execute(
        """
        UPDATE messages
        SET scene_id = ?, position_order = ?
        WHERE id = ?
        """,
        (target_scene_id, new_position, message_id),
    )

    conn.commit()
    return True


def duplicate_scene(
    conn: sqlite3.Connection,
    scene_id: str,
    new_name: str,
) -> str:
    """
    Duplica una scena con tutti i suoi messaggi.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    scene_id:
        ID della scena da duplicare.
    new_name:
        Nome per la nuova scena duplicata.

    Returns
    -------
    str
        L'ID della nuova scena duplicata.
    """
    cur = conn.cursor()
    # Leggi i messaggi prima di iniziare le scritture
    cur.execute(
        "SELECT character_id, author_name, content_original, content_enhanced, ts, source, position_order, is_summary FROM messages WHERE scene_id = ? ORDER BY position_order",
        (scene_id,),
    )
    rows = cur.fetchall()
    new_scene_id = new_id()
    cur.execute(
        "INSERT INTO scenes(id, title, created_at, updated_at) VALUES(?, ?, datetime('now'), datetime('now'))",
        (new_scene_id, new_name),
    )
    for row in rows:
        char_id, author, content_orig, content_enh, ts, source, pos, is_sum = row
        cur.execute(
            """INSERT INTO messages(id, scene_id, character_id, author_name, content_original,
               content_enhanced, ts, source, position_order, is_summary)
               VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (new_id(), new_scene_id, char_id, author, content_orig, content_enh, ts, source, pos, is_sum),
        )
    conn.commit()
    return new_scene_id


def merge_scenes(
    conn: sqlite3.Connection,
    scene_id_a: str,
    scene_id_b: str,
    new_name: str,
) -> str:
    """
    Unisce due scene in una nuova scena con tutti i messaggi di entrambe.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    scene_id_a:
        ID della prima scena da unire.
    scene_id_b:
        ID della seconda scena da unire.
    new_name:
        Nome per la nuova scena unita.

    Returns
    -------
    str
        L'ID della nuova scena unita.
    """
    cur = conn.cursor()
    new_scene_id = new_id()
    cur.execute(
        "INSERT INTO scenes(id, title, created_at, updated_at) VALUES(?, ?, datetime('now'), datetime('now'))",
        (new_scene_id, new_name),
    )
    # Copia messaggi da A poi da B, riassegnando position_order contigue
    cur.execute(
        "SELECT character_id, author_name, content_original, content_enhanced, ts, source, is_summary FROM messages WHERE scene_id = ? ORDER BY position_order",
        (scene_id_a,),
    )
    rows_a = cur.fetchall()
    cur.execute(
        "SELECT character_id, author_name, content_original, content_enhanced, ts, source, is_summary FROM messages WHERE scene_id = ? ORDER BY position_order",
        (scene_id_b,),
    )
    rows_b = cur.fetchall()
    for pos, row in enumerate(rows_a + rows_b, start=1):
        char_id, author, content_orig, content_enh, ts, source, is_sum = row
        cur.execute(
            """INSERT INTO messages(id, scene_id, character_id, author_name, content_original,
               content_enhanced, ts, source, position_order, is_summary)
               VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (new_id(), new_scene_id, char_id, author, content_orig, content_enh, ts, source, pos, is_sum),
        )
    conn.commit()
    return new_scene_id
