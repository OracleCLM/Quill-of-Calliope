"""
Modulo di gestione delle reazioni per il database di Calliope.

Questo modulo è stato riscritto per utilizzare la tabella reale
``scene_reactions`` presente nello schema del database.  Le funzioni
forniscono:

* ``add_reaction`` – inserisce una nuova reazione associata a un
  ``message_id`` e a un ``character_id`` (l'ID della scena viene
  ricavato dal messaggio).
* ``list_reactions`` – restituisce le reazioni per un dato
  ``message_id`` ordinate per data di creazione.

Le funzioni operano su un oggetto ``sqlite3.Connection`` passato
esplicitamente, così da poter essere usate sia in produzione sia nei
test con un DB temporaneo.
"""

from __future__ import annotations

import sqlite3
from typing import List, Mapping, Optional

# Importiamo utility generiche dal package ``app.db``.
# Si assume che ``app.db`` esponga:
#   - ``init_schema(conn)`` per creare lo schema completo del DB.
#   - ``new_id()`` per generare un ID unico (usato per le tabelle che
#     non hanno AUTOINCREMENT).
try:
    # Importiamo in modo dinamico per evitare errori se il modulo non è
    # presente al momento del parsing del file.
    from app.db import new_id  # type: ignore
except Exception:  # pragma: no cover
    # Fallback di sicurezza: se la funzione non è disponibile, usiamo
    # ``None`` e lasciamo che SQLite gestisca l'autoincrement.
    new_id = None  # type: ignore


def add_reaction(
    conn: sqlite3.Connection,
    *,
    message_id: int,
    character_id: int,
    emoji: Optional[str] = None,
) -> int:
    """
    Inserisce una nuova reazione nella tabella ``scene_reactions``.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    message_id:
        ID del messaggio a cui la reazione si riferisce.
    character_id:
        ID del personaggio che ha effettuato la reazione.
    emoji:
        Simbolo della reazione (es. ``👍``).  Se ``None`` viene inserito
        una stringa vuota.

    Returns
    -------
    int
        L'ID della riga appena inserita.
    """
    # Recuperiamo lo ``scene_id`` dal messaggio, poiché la tabella
    # ``scene_reactions`` richiede anche questo campo.
    cur = conn.cursor()
    cur.execute(
        "SELECT scene_id FROM messages WHERE id = ?",
        (message_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"Message with id {message_id} does not exist")
    scene_id: int = row[0]

    # Prepariamo i valori da inserire.
    reaction_text = emoji if emoji is not None else ""

    # Se la tabella prevede un campo ``id`` con AUTOINCREMENT possiamo
    # ometterlo; altrimenti, usiamo ``new_id()`` se disponibile.
    if new_id is not None:
        reaction_id = new_id()
        cur.execute(
            """
            INSERT INTO scene_reactions
                (id, scene_id, character_id, message_id, reaction)
            VALUES (?, ?, ?, ?, ?)
            """,
            (reaction_id, scene_id, character_id, message_id, reaction_text),
        )
    else:
        cur.execute(
            """
            INSERT INTO scene_reactions
                (scene_id, character_id, message_id, reaction)
            VALUES (?, ?, ?, ?)
            """,
            (scene_id, character_id, message_id, reaction_text),
        )
        reaction_id = cur.lastrowid

    conn.commit()
    return reaction_id


def list_reactions(
    conn: sqlite3.Connection,
    *,
    message_id: int,
) -> List[Mapping[str, object]]:
    """
    Restituisce la lista delle reazioni associate a ``message_id``,
    ordinate per data di creazione (campo ``created_at`` se presente).

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    message_id:
        ID del messaggio di cui si vogliono le reazioni.

    Returns
    -------
    List[Mapping[str, object]]
        Lista di dizionari, ciascuno contenente le colonne della tabella
        ``scene_reactions``.
    """
    cur = conn.cursor()
    # Verifichiamo se la tabella possiede il campo ``created_at`` per
    # ordinare correttamente; altrimenti, ordiniamo per ``id``.
    cur.execute(
        "PRAGMA table_info(scene_reactions)"
    )
    columns_info = cur.fetchall()
    column_names = {info[1] for info in columns_info}
    order_by = "created_at" if "created_at" in column_names else "id"

    query = f"""
        SELECT *
        FROM scene_reactions
        WHERE message_id = ?
        ORDER BY {order_by}
    """
    cur.execute(query, (message_id,))
    rows = cur.fetchall()
    # Convertiamo le tuple in dict per comodità di test
    col_desc = [desc[0] for desc in cur.description]
    result = [dict(zip(col_desc, row)) for row in rows]

    # Normalizziamo il nome della colonna della reazione: se lo schema
    # usa ``emoji`` la chiave viene rinominata in ``reaction`` per
    # coerenza con l'API pubblica.
    for entry in result:
        if "emoji" in entry and "reaction" not in entry:
            entry["reaction"] = entry.pop("emoji")

    return result
