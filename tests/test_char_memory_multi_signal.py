"""TCM1-TCM8: char_memory multi-signal retrieval + self-editing tools tests."""
from __future__ import annotations

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import app.calliope_shell.char_memory as cm
from app.calliope_shell.char_memory_tools import (
    char_memory_append,
    char_memory_replace,
)


# ── Fixture: isolated DB for each test ───────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    orig = cm._DB_PATH
    cm._DB_PATH = tmp_path / "test_multi_signal.db"
    cm.init_db()
    yield
    cm._DB_PATH = orig
    cm.init_db()


# ── TCM1: schema migration idempotent ────────────────────────────────────────

def test_tcm1_schema_migration_idempotent():
    """Running init_db twice must not raise or duplicate schema."""
    cm.init_db()
    cm.init_db()
    import sqlite3
    with sqlite3.connect(str(cm._DB_PATH)) as c:
        cols = {row[1] for row in c.execute("PRAGMA table_info(char_state)")}
        assert "entities" in cols
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "char_facts" in tables
        assert "char_facts_meta" in tables


# ── TCM2: retrieve_multi_signal returns dict with signals ────────────────────

def test_tcm2_retrieve_multi_signal_returns_signals():
    """retrieve_multi_signal must return list with 'signals' key containing bm25/entity."""
    cm.append_fact("Aurora", "ha incontrato un cultista vampirizzato nella cripta", scope="L1")
    cm.append_fact("Aurora", "Aurora ha combattuto il vampiro con la spada Dawnbreaker", scope="L1")

    results = cm.retrieve_multi_signal("Aurora", "vampiro cultista")
    assert isinstance(results, list)
    assert len(results) > 0
    for r in results:
        assert "fact_text" in r
        assert "score" in r
        assert "signals" in r
        assert "bm25" in r["signals"]
        assert "entity" in r["signals"]


# ── TCM3: entity boost on known character name ───────────────────────────────

def test_tcm3_entity_boost_character_name():
    """A fact mentioning 'Aurora' should rank higher when query contains 'Aurora'."""
    cm.append_fact("Aurora", "Aurora ha salvato il villaggio di Eldryth", scope="L1")
    cm.append_fact("Aurora", "il tempo era tempestoso quella notte oscura senza luna", scope="L1")

    results = cm.retrieve_multi_signal("Aurora", "Aurora Eldryth")
    assert len(results) > 0
    top = results[0]
    assert "Aurora" in top["fact_text"] or top["signals"]["entity"] > 0


# ── TCM4: cosine stub redistributes weights (graceful) ───────────────────────

def test_tcm4_cosine_stub_redistribution():
    """retrieve_multi_signal works even without cosine (cosine stub raises internally)."""
    cm.append_fact("Philly", "Philly ha perso il suo mantello nella foresta", scope="L1")
    results = cm.retrieve_multi_signal("Philly", "mantello foresta")
    assert isinstance(results, list)
    # Should still return results via BM25 + entity, even if cosine stub absent


# ── TCM5: append_fact L1/L2 works, L0 blocked ───────────────────────────────

def test_tcm5_append_scope_enforcement():
    res_l1 = char_memory_append("Aurora", "L1 test fact", scope="L1")
    assert res_l1["success"] is True
    assert res_l1["scope"] == "L1"

    res_l2 = char_memory_append("Aurora", "L2 archive fact", scope="L2")
    assert res_l2["success"] is True
    assert res_l2["scope"] == "L2"

    res_l0 = char_memory_append("Aurora", "Trying to write to L0", scope="L0")
    assert res_l0["success"] is False
    assert "protected" in res_l0["error"].lower() or "L0" in res_l0["error"]


# ── TCM6: replace_fact approval gate ─────────────────────────────────────────

def test_tcm6_replace_approval_gate():
    char_memory_append("Aurora", "Aurora è amica di Philly", scope="L1")

    # Without approval → requires_approval
    result = char_memory_replace("Aurora", "amica di Philly", "rivale di Philly", scope="L1", approved=False)
    assert result.get("requires_approval") is True
    assert result.get("success") is False

    # With approval → executes
    result = char_memory_replace("Aurora", "amica di Philly", "rivale di Philly", scope="L1", approved=True)
    assert result.get("success") is True
    assert result.get("replaced", 0) >= 1


# ── TCM7: L0 blocked in replace ──────────────────────────────────────────────

def test_tcm7_l0_blocked_in_replace():
    result = char_memory_replace("Aurora", "any text", "new text", scope="L0", approved=True)
    assert result["success"] is False
    assert "L0" in result["error"] or "protected" in result["error"].lower()


# ── TCM8: 30-query precision@10 benchmark ≥70% ──────────────────────────────

def test_tcm8_precision_at_10_benchmark():
    """50-query precision@10 benchmark — Vesta parity target ≥80%.

    Expanded from 30q (70% threshold) to 50q (80% threshold) per
    R-CALLIOPE-RECIPROCAL-VALIDATION-VESTA sprint.
    Tuning: FTS5 prefix matching + w_bm25=0.60/w_entity=0.40 (Vesta defaults).
    """
    CHAR = "TestHero"
    labeled_facts = [
        ("combatte con la spada nella foresta oscura", ["foresta", "spada", "combatte"]),
        ("incontra un elfo misterioso al mercato", ["elfo", "mercato"]),
        ("guarda le stelle nella notte silenziosa", ["stelle", "notte"]),
        ("salva il villaggio dal drago rosso", ["drago", "villaggio"]),
        ("trova un libro antico nella biblioteca", ["libro", "biblioteca"]),
        ("parla con il re nel castello", ["re", "castello"]),
        ("attraversa il ponte di pietra rotto", ["ponte", "pietra"]),
        ("scopre un segreto nella cantina buia", ["segreto", "cantina"]),
        ("addestra un lupo grigio nella pianura", ["lupo", "pianura"]),
        ("cura una ferita alla spalla sinistra", ["ferita", "spalla"]),
    ]
    for fact_text, _kw in labeled_facts:
        cm.append_fact(CHAR, fact_text, scope="L1")

    # 50 queries: original 30 + 20 expansion (Vesta parity set)
    queries = [
        # ── Original 30 ─────────────────────────────────────────────────────
        ("foresta spada combatte", "combatte con la spada"),
        ("elfo mercato", "elfo misterioso"),
        ("stelle notte", "stelle nella notte"),
        ("drago villaggio", "drago rosso"),
        ("libro biblioteca", "libro antico"),
        ("re castello", "castello"),
        ("ponte pietra", "ponte di pietra"),
        ("segreto cantina", "cantina buia"),
        ("lupo pianura", "lupo grigio"),
        ("ferita spalla", "ferita alla spalla"),
        ("spada oscura foresta", "combatte con la spada"),
        ("elfo strano", "elfo misterioso"),
        ("cielo notturno stelle", "stelle nella notte"),
        ("nemico drago", "drago rosso"),
        ("tomo antico", "libro antico"),
        ("sovrano palazzo", "re nel castello"),
        ("traversare ponte", "ponte di pietra"),
        ("mistero segreto buio", "cantina buia"),
        ("addestrare animale", "lupo grigio"),
        ("cura lesione", "ferita alla spalla"),
        ("combattimento armi", "combatte con la spada"),
        ("commercio mercato", "elfo mercato"),
        ("astronomia cielo", "stelle nella notte"),
        ("mostro drago", "drago rosso"),
        ("conoscenza libro", "libro antico"),
        ("governante re", "re nel castello"),
        ("costruzione ponte", "ponte di pietra"),
        ("mistero oscuro", "cantina buia"),
        ("bestia selvaggia", "lupo grigio"),
        ("medicazione ferita", "ferita alla spalla"),
        # ── Expansion 20 (Vesta parity, deterministic seed) ──────────────────
        ("spada nella foresta buia", "combatte con la spada"),
        ("elfo al mercato cittadino", "elfo misterioso"),
        ("notte stellata silenziosa", "stelle nella notte"),
        ("drago nemico del villaggio", "drago rosso"),
        ("libro raro trovato in biblioteca", "libro antico"),
        ("il re ordina nel castello", "re nel castello"),
        ("ponte di pietra vecchio", "ponte di pietra"),
        ("segreto nascosto in cantina", "cantina buia"),
        ("lupo addestrato in pianura", "lupo grigio"),
        ("ferita curata sulla spalla", "ferita alla spalla"),
        ("combatte con la lancia in foresta", "combatte con la spada"),
        ("elfo incontrato misteriosamente", "elfo misterioso"),
        ("stelle e luna nella notte", "stelle nella notte"),
        ("drago sconfitto e villaggio salvo", "drago rosso"),
        ("libro di saggezza in biblioteca", "libro antico"),
        ("re potente nel castello", "re nel castello"),
        ("attraversare il ponte rotto", "ponte di pietra"),
        ("cantina con segreto oscuro", "cantina buia"),
        ("addestramento del lupo in pianura", "lupo grigio"),
        ("cura della ferita alla spalla", "ferita alla spalla"),
    ]

    hits = 0
    total = len(queries)
    for query_text, expected_kw in queries:
        results = cm.retrieve_multi_signal(CHAR, query_text, top_k=10)
        found = any(expected_kw.split()[0] in r["fact_text"] for r in results)
        if found:
            hits += 1

    precision = hits / total
    assert precision >= 0.80, (
        f"precision@10={precision:.2%} < 80% threshold "
        f"({hits}/{total} queries returned expected fact)"
    )
