"""Test per scene_retrieval."""

from pathlib import Path


from app.calliope_shell.lore_kb import LoreEntry, LoreStore
from app.calliope_shell.scene_retrieval import retrieve_scene_lore


def test_retrieve_scene_lore(tmp_path: Path) -> None:
    """Verifica il comportamento di retrieve_scene_lore."""
    # Setup store
    store = LoreStore(str(tmp_path / "lore.json"))

    # Add entries
    store.add_entry(
        LoreEntry(id="e-drago", title="Drago", keys=["drago"], content="...")
    )
    store.add_entry(
        LoreEntry(id="e-const", title="Mondo", content="...", constant=True)
    )

    # (a) Test con stringa vuota
    assert retrieve_scene_lore("", store) == []

    # (b) Test con key match 'drago'
    result_dragon = retrieve_scene_lore("C'è un drago qui.", store)
    ids_dragon = [e.id for e in result_dragon]
    assert "e-drago" in ids_dragon

    # (c) Test entry constant sempre presente
    # Usiamo un testo senza chiavi per verificare che solo le costanti escano
    result_const = retrieve_scene_lore("Testo senza chiavi.", store)
    ids_const = [e.id for e in result_const]
    assert "e-const" in ids_const
    assert "e-drago" not in ids_const

    # (d) Test max_entries limit
    # Con "drago" matchiamo sia costanti che chiavi, ma limitiamo a 1
    result_limited = retrieve_scene_lore("Vide un drago.", store, max_entries=1)
    assert len(result_limited) == 1
    # Le costanti hanno priorità, quindi ci aspettiamo e-const
    assert result_limited[0].id == "e-const"
