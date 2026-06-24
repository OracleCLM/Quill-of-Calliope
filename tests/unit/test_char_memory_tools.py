"""
Unit test char_memory_tools.py — logica di validazione (paths senza DB).

Contratto:
  - append: args vuoti → error; scope invalido → error; L0 bloccato (da replace)
  - replace: args vuoti → error; L0 protetto → error; scope invalido → error;
    approved=False → requires_approval; approved=True → delega a replace_fact
  - recall: args vuoti → error; con args → successo delegato
  - list_facts: char vuoto → success con lista vuota o errore
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.char_memory_tools import (
    char_memory_append,
    char_memory_list_facts,
    char_memory_recall,
    char_memory_replace,
)

_MOD = "app.calliope_shell.char_memory_tools"


# ── char_memory_append ────────────────────────────────────────────────────────

def test_append_empty_char_name():
    result = char_memory_append("", "some fact")
    assert not result["success"]
    assert "required" in result["error"]


def test_append_empty_fact():
    result = char_memory_append("Aurora", "")
    assert not result["success"]
    assert "required" in result["error"]


def test_append_invalid_scope():
    result = char_memory_append("Aurora", "some fact", scope="L0")
    assert not result["success"]
    assert "L1 or L2" in result["error"]


def test_append_valid_delegates_to_append_fact():
    with patch(f"{_MOD}.append_fact", return_value="fact-uuid-123") as mock_af:
        result = char_memory_append("Aurora", "Aurora è una strega", scope="L1")
    mock_af.assert_called_once_with("Aurora", "Aurora è una strega", scope="L1")
    assert result["success"]
    assert result["fact_id"] == "fact-uuid-123"
    assert result["scope"] == "L1"


def test_append_when_append_fact_returns_none():
    with patch(f"{_MOD}.append_fact", return_value=None):
        result = char_memory_append("Aurora", "some fact")
    assert not result["success"]
    assert "failed" in result["error"]


# ── char_memory_replace ───────────────────────────────────────────────────────

def test_replace_empty_args():
    result = char_memory_replace("", "old", "new")
    assert not result["success"]

def test_replace_l0_blocked():
    result = char_memory_replace("Aurora", "old", "new", scope="L0", approved=True)
    assert not result["success"]
    assert "L0" in result["error"]


def test_replace_invalid_scope():
    result = char_memory_replace("Aurora", "old", "new", scope="L3", approved=True)
    assert not result["success"]
    assert "L1 or L2" in result["error"]


def test_replace_requires_approval_gate():
    result = char_memory_replace("Aurora", "old fact", "new fact", approved=False)
    assert not result["success"]
    assert result.get("requires_approval") is True


def test_replace_approved_delegates():
    mock_result = {"replaced": 1, "old": "old fact", "new": "new fact"}
    with patch(f"{_MOD}.replace_fact", return_value=mock_result) as mock_rf:
        result = char_memory_replace("Aurora", "old fact", "new fact", scope="L1", approved=True)
    mock_rf.assert_called_once_with("Aurora", "old fact", "new fact", scope="L1")
    assert result["replaced"] == 1


# ── char_memory_recall ────────────────────────────────────────────────────────

def test_recall_empty_char():
    result = char_memory_recall("", "some query")
    assert not result["success"]


def test_recall_empty_query():
    result = char_memory_recall("Aurora", "")
    assert not result["success"]


def test_recall_delegates_to_retrieve_multi_signal():
    fake_hits = [{"fact_text": "Aurora è potente", "score": 0.9}]
    with patch(f"{_MOD}.retrieve_multi_signal", return_value=fake_hits) as mock_r:
        result = char_memory_recall("Aurora", "poteri magici", top_k=3)
    mock_r.assert_called_once_with("Aurora", "poteri magici", top_k=3)
    assert result["success"]
    assert result["count"] == 1
    assert result["results"] == fake_hits


# ── char_memory_list_facts ────────────────────────────────────────────────────

def test_list_facts_delegates_to_get_facts():
    fake_facts = [{"fact_text": "Aurora ha occhi viola", "scope": "L1"}]
    with patch(f"{_MOD}.get_facts", return_value=fake_facts) as mock_g:
        result = char_memory_list_facts("Aurora", scope="L1")
    mock_g.assert_called_once_with("Aurora", scope="L1")
    assert result["success"]
    assert result["count"] == 1
    assert result["facts"] == fake_facts


def test_list_facts_no_scope_filter():
    with patch(f"{_MOD}.get_facts", return_value=[]) as mock_g:
        result = char_memory_list_facts("Aurora")
    mock_g.assert_called_once_with("Aurora", scope=None)
    assert result["success"]
    assert result["count"] == 0
