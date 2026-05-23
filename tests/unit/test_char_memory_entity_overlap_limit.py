"""Regression tests for P1 #10 — N+1 entity-overlap full-scan.

Audit ref: docs/audit/CALLIOPE_DEEP_REVIEW_2026-05-22.md §2 P1 #10
Fix: cap at _ENTITY_OVERLAP_SCAN_LIMIT most-recent facts per char.
"""
from __future__ import annotations

import time
import uuid

import pytest

from app.calliope_shell import char_memory


@pytest.fixture
def fresh_char(tmp_path, monkeypatch):
    """Isolated DB per test — no contamination of real char_memory.db."""
    db = tmp_path / "test_char_memory.db"
    monkeypatch.setattr(char_memory, "_DB_PATH", db)
    char_memory.init_db()
    yield "TestChar_" + uuid.uuid4().hex[:8]


def _append_n_facts(name: str, n: int) -> None:
    """Insert n facts via the public append API."""
    for i in range(n):
        char_memory.append_fact(name, f"fact {i} about {name}", scope="L1")


def test_entity_overlap_limit_constant_exists():
    assert hasattr(char_memory, "_ENTITY_OVERLAP_SCAN_LIMIT")
    assert isinstance(char_memory._ENTITY_OVERLAP_SCAN_LIMIT, int)
    assert char_memory._ENTITY_OVERLAP_SCAN_LIMIT > 0


def test_entity_overlap_query_has_limit_clause():
    """Static-source guarantee: the entity-overlap SQL must use LIMIT + ?."""
    import inspect
    src = inspect.getsource(char_memory.retrieve_multi_signal)
    # Source may be split across continuation strings; check tokens individually.
    assert "char_facts" in src
    assert "ORDER BY created_at DESC" in src
    assert "LIMIT ?" in src
    assert "_ENTITY_OVERLAP_SCAN_LIMIT" in src


def test_entity_overlap_runtime_stable_on_large_corpus(fresh_char, monkeypatch):
    """With LIMIT applied, retrieval latency must stay bounded on big corpora."""
    name = fresh_char
    monkeypatch.setattr(char_memory, "_ENTITY_OVERLAP_SCAN_LIMIT", 100)

    _append_n_facts(name, 1000)

    t0 = time.monotonic()
    results = char_memory.retrieve_multi_signal(name, "fact 5")
    elapsed = time.monotonic() - t0

    # Generous ceiling — pre-fix would scan 1000 rows + JSON-parse all entities;
    # post-fix scans at most 100.
    assert elapsed < 2.0, f"retrieve_multi_signal too slow: {elapsed:.2f}s"
    assert isinstance(results, list)
