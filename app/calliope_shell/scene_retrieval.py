"""Helper per il recupero del contesto lore nelle scene."""

from app.calliope_shell.lore_kb import LoreEntry, LoreStore


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
