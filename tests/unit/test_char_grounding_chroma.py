"""Contract test (GO-import Step 1: ChromaDB-wire char-grounding).

Wira la ChromaDB .chroma_calliope GIA' popolata (calliope_characters=118) al char-grounding
del draft-gen. MVP embedder-independent: lookup per slug nella collection calliope_characters
(metadata where, NO query-embeddings → niente dipendenza nomic-768). Ritorna il profilo char
come grounding. La RAG semantica sui messaggi (768-dim) è phase-2.

Hermetico: store chroma TEMP seedato (nessun dato personale reale).
"""
import chromadb

from app.calliope_shell.char_grounding import retrieve_char_grounding


def _seed_chroma(tmp_path):
    path = str(tmp_path / "chroma")
    cl = chromadb.PersistentClient(path=path)
    col = cl.get_or_create_collection("calliope_characters")
    col.add(
        ids=["c1", "c2"],
        documents=["Kikyo is a snow kitsune who left the shrine to train.",
                   "Arianna is a fiery exile with a sharp tongue."],
        metadatas=[{"slug": "kikyo"}, {"slug": "arianna-exilio-the-fiery"}],
    )
    return path


def test_grounding_by_slug_returns_profile(tmp_path):
    path = _seed_chroma(tmp_path)
    facts = retrieve_char_grounding("Kikyo", chroma_path=path)
    assert isinstance(facts, list) and len(facts) >= 1
    assert any("snow kitsune" in f for f in facts)


def test_grounding_unknown_char_returns_empty(tmp_path):
    path = _seed_chroma(tmp_path)
    facts = retrieve_char_grounding("Nessuno", chroma_path=path)
    assert facts == []


def test_grounding_missing_store_returns_empty(tmp_path):
    # store inesistente → degrada a [], non solleva (robustezza draft-gen)
    facts = retrieve_char_grounding("Kikyo", chroma_path=str(tmp_path / "nope"))
    assert facts == []
