"""ChromaDB-wire per il char-grounding del draft-gen (GO-import Step 1).

Lookup char-profile per slug nella collection calliope_characters (.chroma_calliope, gia'
popolata 118 char). Embedder-independent (metadata where, NO query-embeddings). La RAG
semantica sui messaggi (768-dim/nomic) e' phase-2.
"""
from __future__ import annotations


def retrieve_char_grounding(char_name: str, chroma_path: str = ".chroma_calliope", top_k: int = 2) -> list:
    """
    Ritorna il/i documento-profilo del personaggio dalla ChromaDB come grounding (vedi
    tests/unit/test_char_grounding_chroma.py):
      - slug = char_name.lower().strip().replace(" ", "-"); query calliope_characters where slug==slug.
      - ritorna la lista dei documents (max top_k); char sconosciuto o store assente -> [] (degrada).
    """
    raise NotImplementedError("Step 1 char-grounding: impl worker")
