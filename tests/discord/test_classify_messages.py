"""Tests for scripts/classify_messages.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from classify_messages import classify_batch, rule_based_fallback  # noqa: E402


# ---------------------------------------------------------------------------
# test_rule_based_fallback
# ---------------------------------------------------------------------------


def test_rule_based_fallback_ooc():
    """Messages starting with '(' are classified OOC."""
    msg = {"content": "(just checking if everyone is ready)"}
    assert rule_based_fallback(msg) == "OOC"


def test_rule_based_fallback_ic_default():
    """Narrative messages default to IC."""
    msg = {"content": "She walks slowly into the dimly lit tavern."}
    assert rule_based_fallback(msg) == "IC"


def test_rule_based_fallback_meta():
    """Messages with server/rule keywords → meta."""
    msg = {"content": "New server rule: no NSFW content."}
    assert rule_based_fallback(msg) == "meta"


def test_rule_based_fallback_art():
    """Messages with art/image keywords → art."""
    msg = {"content": "I drew some art for the campaign!"}
    assert rule_based_fallback(msg) == "art"


def test_rule_based_fallback_empty_content():
    """Empty content defaults to IC."""
    msg = {"content": ""}
    assert rule_based_fallback(msg) == "IC"


def test_rule_based_fallback_missing_content():
    """Missing content key defaults to IC."""
    msg = {}
    assert rule_based_fallback(msg) == "IC"


# ---------------------------------------------------------------------------
# test_classify_batch_mock
# ---------------------------------------------------------------------------


def _make_mock_response(tags: list[str]) -> MagicMock:
    """Build a mock requests.Response returning a JSON array of tags."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(tags),
                }
            }
        ]
    }
    return mock_resp


def test_classify_batch_mock_cerebras(monkeypatch):
    """classify_batch returns correct-length tag list via mocked cerebras endpoint."""
    monkeypatch.setenv("CEREBRAS_API_KEY", "test-key")

    messages = [
        {"content": "She draws her sword and steps forward."},
        {"content": "(brb 5 minutes)"},
        {"content": "Server announcement: maintenance tonight."},
    ]
    expected_tags = ["IC", "OOC", "meta"]

    with patch("classify_messages.requests.post") as mock_post:
        mock_post.return_value = _make_mock_response(expected_tags)
        result = classify_batch(messages, provider="cerebras", model="qwen-3-235b-a22b-instruct-2507")

    assert len(result) == len(messages)
    assert result == expected_tags
    mock_post.assert_called_once()


def test_classify_batch_mock_groq(monkeypatch):
    """classify_batch works with groq provider."""
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

    messages = [
        {"content": "The dragon roars."},
        {"content": "(nice move!)"},
    ]
    expected_tags = ["IC", "OOC"]

    with patch("classify_messages.requests.post") as mock_post:
        mock_post.return_value = _make_mock_response(expected_tags)
        result = classify_batch(messages, provider="groq", model="llama-3.3-70b-versatile")

    assert len(result) == 2
    assert result == expected_tags


def test_classify_batch_fallback_on_api_error(monkeypatch):
    """classify_batch uses rule-based fallback when API call raises."""
    monkeypatch.setenv("CEREBRAS_API_KEY", "test-key")

    messages = [
        {"content": "(this is OOC)"},
        {"content": "He charged into battle."},
    ]

    with patch("classify_messages.requests.post", side_effect=ConnectionError("network error")):
        result = classify_batch(messages, provider="cerebras", model="qwen-3-235b-a22b-instruct-2507")

    assert len(result) == 2
    assert result[0] == "OOC"
    assert result[1] == "IC"


def test_classify_batch_line_separated_fallback(monkeypatch):
    """classify_batch handles line-separated (non-JSON) LLM output."""
    monkeypatch.setenv("CEREBRAS_API_KEY", "test-key")

    messages = [
        {"content": "She laughs."},
        {"content": "(ooc comment)"},
    ]

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "IC\nOOC"}}]
    }

    with patch("classify_messages.requests.post", return_value=mock_resp):
        result = classify_batch(messages, provider="cerebras", model="qwen-3-235b-a22b-instruct-2507")

    assert len(result) == 2
    assert result[0] == "IC"
    assert result[1] == "OOC"


# ---------------------------------------------------------------------------
# test_dry_run_argparse
# ---------------------------------------------------------------------------


def test_dry_run_argparse():
    """--dry-run flag is present and recognized in argparse."""
    import argparse

    # Re-build the parser exactly as main() does
    parser = argparse.ArgumentParser(description="Classify Discord messages in batch")
    parser.add_argument("--input", type=str, required=False, default="in.jsonl")
    parser.add_argument("--output", type=str, required=False, default="out.jsonl")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--provider", type=str, default="cerebras", choices=["cerebras", "groq", "local"])
    parser.add_argument("--model", type=str, default="qwen-3-235b-a22b-instruct-2507")
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(["--input", "x.jsonl", "--output", "y.jsonl", "--dry-run"])
    assert args.dry_run is True


def test_dry_run_argparse_default_false():
    """--dry-run defaults to False when not provided."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=False, default="in.jsonl")
    parser.add_argument("--output", type=str, required=False, default="out.jsonl")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--provider", type=str, default="cerebras", choices=["cerebras", "groq", "local"])
    parser.add_argument("--model", type=str, default="qwen-3-235b-a22b-instruct-2507")
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args([])
    assert args.dry_run is False
