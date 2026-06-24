"""
Retrieval helpers per context injection nel prompt (E1 lore, E2 schede personaggi).

- lore_retrieval_for_scene  → voci lore rilevanti (E1)
- sheet_retrieval_for_scene → schede personaggi attivi in scena (E2)

Output usato da refine-fn (E3) per popolare messages.content_enhanced.
"""
from __future__ import annotations

import sqlite3
from typing import List

from app.calliope_shell.lore_kb import LoreEntry, LoreStore
from app.db.characters import list_characters_in_scene


def lore_retrieval_for_scene(
    text: str,
    lore_store: LoreStore,
    max_entries: int = 20,
) -> List[LoreEntry]:
    """Ritorna le voci lore rilevanti per il testo della scena (E1).

    Delega a LoreStore.triggered_entries: constant entries + key-match.
    """
    return lore_store.triggered_entries(text, max_entries=max_entries)


def sheet_retrieval_for_scene(
    conn: sqlite3.Connection,
    scene_id: str,
) -> List[dict]:
    """Ritorna le schede dei personaggi attivi nella scena (E2).

    Per ogni personaggio nel roster (scene_characters), recupera i blocchi
    di testo in character_sheets associati tramite character_id.

    Returns list of {"name": str, "role": str, "sheets": [str, ...]}.
    """
    chars = list_characters_in_scene(conn, scene_id)
    results: List[dict] = []
    for char in chars:
        char_id = char.get("id")
        char_name = char.get("name", "")
        role = char.get("role", "")
        sheets: List[str] = []
        if char_id:
            cur = conn.execute(
                "SELECT content FROM character_sheets"
                " WHERE character_id = ? ORDER BY position_order",
                (char_id,),
            )
            sheets = [row[0] for row in cur.fetchall()]
        results.append({"name": char_name, "role": role, "sheets": sheets})
    return results
