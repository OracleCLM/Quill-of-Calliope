"""
Modulo di gestione delle reazioni per il database di Calliope.

Fornisce funzioni di utilità per:
- Inizializzare le tabelle necessarie (`init_db`).
- Aggiungere una reazione (`add_reaction`).
- Recuperare le reazioni (`list_reactions`).

Le funzioni operano su un oggetto ``sqlite3.Connection`` passato
esplicitamente, così da poter essere usate sia in produzione sia nei
test con un DB temporaneo in‑memory.
"""

from __future__ import annotations

import sqlite3
from typing import List, Mapping, Optional


def init_db(conn: sqlite3.Connection) -> None:
    """
    Crea le tabelle di base se non esistono.

    Tabelle:
    - scenes (id)
    - characters (id, scene_id)
    - messages (id, scene_id, character_id, content)
    - reactions (id, scene_id, character_id, message_id, reaction)

    La funzione è idempotente.
    """
    cur = conn.cursor()
    # Le tabelle ``scenes``, ``characters`` e ``messages`` sono
    # semplificate: bastano gli ID per i test.
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS scenes (
            id INTEGER PRIMARY KEY AUTOINCREMENT
        );

        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scene_id INTEGER NOT NULL,
            FOREIGN KEY (scene_id) REFERENCES scenes(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scene_id INTEGER NOT NULL,
            character_id INTEGER NOT NULL,
            content TEXT,
            FOREIGN KEY (scene_id) REFERENCES scenes(id) ON DELETE CASCADE,
            FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scene_id INTEGER NOT NULL,
            character_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            reaction TEXT NOT NULL,
            FOREIGN KEY (scene_id) REFERENCES scenes(id) ON DELETE CASCADE,
            FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
            FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()


def add_reaction(
    conn: sqlite3.Connection,
    *,
    scene_id: int,
    character_id: int,
    message_id: int,
    reaction: str,
) -> int:
    """
    Inserisce una nuova reazione nella tabella ``reactions``.

    Restituisce l'ID della riga appena inserita.
    """
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO reactions (scene_id, character_id, message_id, reaction)
        VALUES (?, ?, ?, ?)
        """,
        (scene_id, character_id, message_id, reaction),
    )
    conn.commit()
    return cur.lastrowid


def list_reactions(
    conn: sqlite3.Connection,
    *,
    scene_id: Optional[int] = None,
    character_id: Optional[int] = None,
    message_id: Optional[int] = None,
) -> List[Mapping[str, object]]:
    """
    Restituisce una lista di reazioni filtrate opzionalmente per
    ``scene_id``, ``character_id`` e/o ``message_id``.

    Ogni elemento è un mapping con le chiavi:
    ``id``, ``scene_id``, ``character_id``, ``message_id``, ``reaction``.
    """
    cur = conn.cursor()
    query = "SELECT id, scene_id, character_id, message_id, reaction FROM reactions"
    conditions: List[str] = []
    params: List[object] = []

    if scene_id is not None:
        conditions.append("scene_id = ?")
        params.append(scene_id)
    if character_id is not None:
        conditions.append("character_id = ?")
        params.append(character_id)
    if message_id is not None:
        conditions.append("message_id = ?")
        params.append(message_id)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    # Convertiamo le tuple in dict per comodità di test
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in rows]
