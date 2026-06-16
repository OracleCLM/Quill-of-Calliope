"""Helper per il recupero del contesto lore nelle scene."""
import json

from app.calliope_shell.lore_kb import LoreEntry, LoreStore
from app.db.characters import list_characters_in_scene


def retrieve_scene_lore(
    scene_text: str, store: LoreStore, max_entries: int = 20
) -> list[LoreEntry]:
    """
    Recupera le voci di lore rilevanti per una scena.

    Se il testo della scena è vuoto o None, restituisce una lista vuota.
    Altrimenti delega al metodo ``triggered_entries`` del LoreStore.

    Args:
        scene_text: Il testo della scena.
        store: Istanza di LoreStore.
        max_entries: Numero massimo di entry da restituire.

    Returns:
        Lista di LoreEntry.
    """
    if not scene_text:
        return []
    return store.triggered_entries(scene_text, max_entries=max_entries)


def retrieve_scene_sheets(scene_id: str, conn) -> list[dict]:
    """
    Recupera le schede compatte dei personaggi nel roster della scena.

    Args:
        scene_id: ID della scena.
        conn: Connessione al database.

    Returns:
        Lista di dizionari con i dati della scheda.
    """
    sheets = []
    for c in list_characters_in_scene(conn, scene_id):
        try:
            card = json.loads(c["card_json"] or "{}") or {}
        except (TypeError, ValueError):
            card = {}

        sheets.append(
            {
                "character_id": c["id"],
                "name": c["name"],
                "role": c["role"],
                "traits": card.get("traits", []),
                "backstory": (card.get("backstory") or "")[:300],
                "speech_pattern": card.get("speech_pattern", {}),
            }
        )
    return sheets
