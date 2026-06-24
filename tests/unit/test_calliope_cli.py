"""
Unit test per scripts/calliope_cli.py — build_parser + cmd_* functions.

Contratto:
  - build_parser: parse argomenti CLI → Namespace corretto
  - cmd_remember: success → 0, failure → 1
  - cmd_recall: hits → 0, no hits → 0, failure → 1
  - cmd_facts: facts → 0, empty → 0
  - cmd_list: chars → 0, empty → 0
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.calliope_cli import (
    build_parser,
    cmd_facts,
    cmd_list,
    cmd_recall,
    cmd_remember,
)

_CLI = "scripts.calliope_cli"


# ── build_parser ──────────────────────────────────────────────────────────────

def test_parser_remember_minimal():
    p = build_parser()
    ns = p.parse_args(["char", "remember", "Aurora", "Ha ucciso il drago"])
    assert ns.name == "Aurora"
    assert ns.fact == "Ha ucciso il drago"
    assert ns.scope == "L1"


def test_parser_remember_scope_l2():
    p = build_parser()
    ns = p.parse_args(["char", "remember", "Aurora", "segreto", "--scope", "L2"])
    assert ns.scope == "L2"


def test_parser_recall_defaults():
    p = build_parser()
    ns = p.parse_args(["char", "recall", "Aurora", "drago"])
    assert ns.name == "Aurora"
    assert ns.query == "drago"
    assert ns.top_k == 5


def test_parser_recall_top_k():
    p = build_parser()
    ns = p.parse_args(["char", "recall", "Aurora", "drago", "--top-k", "3"])
    assert ns.top_k == 3


def test_parser_facts_no_scope():
    p = build_parser()
    ns = p.parse_args(["char", "facts", "Luna"])
    assert ns.name == "Luna"
    assert ns.scope is None


def test_parser_facts_scope_filter():
    p = build_parser()
    ns = p.parse_args(["char", "facts", "Luna", "--scope", "L2"])
    assert ns.scope == "L2"


def test_parser_list():
    p = build_parser()
    ns = p.parse_args(["char", "list"])
    assert ns.action == "list"


# ── cmd_remember ──────────────────────────────────────────────────────────────

def test_cmd_remember_success():
    ns = SimpleNamespace(name="Aurora", fact="Cavalca un drago", scope="L1")
    mock_result = {
        "success": True,
        "scope": "L1",
        "fact_id": "uuid-1234-5678",
        "fact_preview": "Cavalca un drago",
    }
    with patch(f"{_CLI}.char_memory_append", return_value=mock_result):
        ret = cmd_remember(ns)
    assert ret == 0


def test_cmd_remember_failure_returns_1():
    ns = SimpleNamespace(name="", fact="", scope="L1")
    mock_result = {"success": False, "error": "char_name and fact are required"}
    with patch(f"{_CLI}.char_memory_append", return_value=mock_result):
        ret = cmd_remember(ns)
    assert ret == 1


def test_cmd_remember_prints_fact_id(capsys):
    ns = SimpleNamespace(name="Aurora", fact="Dettaglio importante", scope="L1")
    mock_result = {
        "success": True,
        "scope": "L1",
        "fact_id": "abcd1234efgh5678",
        "fact_preview": "Dettaglio importante",
    }
    with patch(f"{_CLI}.char_memory_append", return_value=mock_result):
        cmd_remember(ns)
    out = capsys.readouterr().out
    assert "abcd1234" in out


# ── cmd_recall ────────────────────────────────────────────────────────────────

def test_cmd_recall_success_with_hits():
    ns = SimpleNamespace(name="Aurora", query="drago", top_k=3)
    hits = [{"scope": "L1", "score": 0.9, "fact_text": "Cavalca un drago rosso"}]
    with patch(f"{_CLI}.char_memory_recall", return_value={"success": True, "results": hits}):
        ret = cmd_recall(ns)
    assert ret == 0


def test_cmd_recall_no_hits(capsys):
    ns = SimpleNamespace(name="Aurora", query="pozione", top_k=5)
    with patch(f"{_CLI}.char_memory_recall", return_value={"success": True, "results": []}):
        ret = cmd_recall(ns)
    out = capsys.readouterr().out
    assert ret == 0
    assert "no facts found" in out


def test_cmd_recall_failure_returns_1():
    ns = SimpleNamespace(name="", query="x", top_k=5)
    with patch(f"{_CLI}.char_memory_recall", return_value={"success": False, "error": "missing arg"}):
        ret = cmd_recall(ns)
    assert ret == 1


# ── cmd_facts ─────────────────────────────────────────────────────────────────

def test_cmd_facts_with_results(capsys):
    ns = SimpleNamespace(name="Aurora", scope=None)
    facts = [{"scope": "L1", "fact_text": "Ha ucciso il drago"}]
    with patch(f"{_CLI}.char_memory_list_facts", return_value={"facts": facts}):
        ret = cmd_facts(ns)
    out = capsys.readouterr().out
    assert ret == 0
    assert "drago" in out


def test_cmd_facts_empty(capsys):
    ns = SimpleNamespace(name="Ghost", scope=None)
    with patch(f"{_CLI}.char_memory_list_facts", return_value={"facts": []}):
        ret = cmd_facts(ns)
    out = capsys.readouterr().out
    assert ret == 0
    assert "No facts" in out


def test_cmd_facts_scope_printed_if_set(capsys):
    ns = SimpleNamespace(name="Aurora", scope="L2")
    with patch(f"{_CLI}.char_memory_list_facts", return_value={"facts": []}):
        cmd_facts(ns)
    out = capsys.readouterr().out
    assert "L2" in out


# ── cmd_list ──────────────────────────────────────────────────────────────────

def test_cmd_list_empty(capsys):
    with patch(f"{_CLI}.list_chars", return_value=[]):
        ret = cmd_list(SimpleNamespace())
    out = capsys.readouterr().out
    assert ret == 0
    assert "No characters" in out


def test_cmd_list_with_chars(capsys):
    chars = [
        {"name": "Aurora", "traits_summary": "strega, coraggiosa", "updated_at": "2026-01-01"},
        {"name": "Luna", "traits_summary": "", "updated_at": "2026-01-02"},
    ]
    with patch(f"{_CLI}.list_chars", return_value=chars):
        ret = cmd_list(SimpleNamespace())
    out = capsys.readouterr().out
    assert ret == 0
    assert "Aurora" in out
    assert "Luna" in out
