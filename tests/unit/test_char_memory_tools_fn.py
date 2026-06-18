"""GAP-38: test unitari per char_memory_tools — append, replace, recall, list_facts."""

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


# ── char_memory_append — validation ─────────────────────────────────────────


def test_append_missing_char_name_returns_error():
    r = char_memory_append("", "un fatto")
    assert r["success"] is False
    assert "required" in r["error"]


def test_append_missing_fact_returns_error():
    r = char_memory_append("Aurora", "")
    assert r["success"] is False
    assert "required" in r["error"]


def test_append_invalid_scope_returns_error():
    r = char_memory_append("Aurora", "un fatto", scope="L0")
    assert r["success"] is False
    assert "L1 or L2" in r["error"]


def test_append_append_fact_returns_none_error():
    with patch(f"{_MOD}.append_fact", return_value=None):
        r = char_memory_append("Aurora", "un fatto")
    assert r["success"] is False
    assert "failed" in r["error"]


def test_append_success():
    with patch(f"{_MOD}.append_fact", return_value="fact-001"):
        r = char_memory_append("Aurora", "ha sconfitto il drago", scope="L1")
    assert r["success"] is True
    assert r["fact_id"] == "fact-001"
    assert r["char_name"] == "Aurora"
    assert r["scope"] == "L1"


def test_append_fact_preview_truncated():
    long_fact = "x" * 200
    with patch(f"{_MOD}.append_fact", return_value="fact-x"):
        r = char_memory_append("A", long_fact)
    assert len(r["fact_preview"]) <= 100


# ── char_memory_replace — validation ────────────────────────────────────────


def test_replace_missing_char_name_returns_error():
    r = char_memory_replace("", "old", "new")
    assert r["success"] is False


def test_replace_missing_old_fact_returns_error():
    r = char_memory_replace("Aurora", "", "new")
    assert r["success"] is False


def test_replace_missing_new_fact_returns_error():
    r = char_memory_replace("Aurora", "old", "")
    assert r["success"] is False


def test_replace_l0_scope_blocked():
    r = char_memory_replace("Aurora", "old", "new", scope="L0")
    assert r["success"] is False
    assert "L0" in r["error"]


def test_replace_invalid_scope_error():
    r = char_memory_replace("Aurora", "old", "new", scope="L9")
    assert r["success"] is False
    assert "L1 or L2" in r["error"]


def test_replace_not_approved_requires_approval():
    r = char_memory_replace("Aurora", "old", "new", scope="L1", approved=False)
    assert r["success"] is False
    assert r.get("requires_approval") is True


def test_replace_approved_calls_replace_fact():
    with patch(f"{_MOD}.replace_fact", return_value={"replaced": 1}) as mock_rf:
        r = char_memory_replace("Aurora", "old", "new", scope="L1", approved=True)
    mock_rf.assert_called_once_with("Aurora", "old", "new", scope="L1")
    assert r == {"replaced": 1}


def test_replace_approved_zero_replaced_still_returns():
    with patch(f"{_MOD}.replace_fact", return_value={"replaced": 0}):
        r = char_memory_replace("Aurora", "not-found", "new", scope="L1", approved=True)
    assert r["replaced"] == 0


# ── char_memory_recall ───────────────────────────────────────────────────────


def test_recall_missing_char_name_error():
    r = char_memory_recall("", "query")
    assert r["success"] is False


def test_recall_missing_query_error():
    r = char_memory_recall("Aurora", "")
    assert r["success"] is False


def test_recall_success_shape():
    with patch(f"{_MOD}.retrieve_multi_signal", return_value=["f1", "f2"]):
        r = char_memory_recall("Aurora", "drago")
    assert r["success"] is True
    assert r["char_name"] == "Aurora"
    assert r["query"] == "drago"
    assert r["count"] == 2
    assert r["results"] == ["f1", "f2"]


# ── char_memory_list_facts ───────────────────────────────────────────────────


def test_list_facts_shape():
    with patch(f"{_MOD}.get_facts", return_value=[{"id": "f1"}, {"id": "f2"}]):
        r = char_memory_list_facts("Aurora")
    assert r["success"] is True
    assert r["char_name"] == "Aurora"
    assert r["count"] == 2
    assert len(r["facts"]) == 2


def test_list_facts_scope_forwarded():
    with patch(f"{_MOD}.get_facts", return_value=[]) as mock_gf:
        char_memory_list_facts("Aurora", scope="L2")
    mock_gf.assert_called_once_with("Aurora", scope="L2")


def test_list_facts_scope_none():
    with patch(f"{_MOD}.get_facts", return_value=[]) as mock_gf:
        char_memory_list_facts("Aurora")
    mock_gf.assert_called_once_with("Aurora", scope=None)
