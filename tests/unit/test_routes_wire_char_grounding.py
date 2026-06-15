"""Contract test (GO Step 1b): le route draft-gen cablano retrieve_char_grounding.

Step 1a ha dato retrieve_char_grounding (ChromaDB char-profile by-slug, validato su dati reali).
Step 1b lo wira nel char_facts delle route draft-gen (messages_next + draft_scene) cosi' il
draft-gen ottiene il grounding del personaggio (oggi char_facts=0 perche' char_memory.db e' vuoto).

Wiring-guard (anti gap-composto, come VG-1b): la verifica e2e (char_facts>0) la fa l'orch.
"""
from pathlib import Path


def test_server_wires_char_grounding_in_both_routes():
    src = (
        Path(__file__).parents[2] / "app" / "calliope_shell" / "server.py"
    ).read_text(encoding="utf-8")
    assert "retrieve_char_grounding" in src, "server.py non importa/usa retrieve_char_grounding"
    assert src.count("retrieve_char_grounding(") >= 2, \
        "entrambe le route draft-gen (messages_next + draft_scene) devono cablarlo"
