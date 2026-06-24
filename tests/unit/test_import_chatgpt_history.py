"""Unit test per scripts/import_chatgpt_history.py.

Copre:
  - _is_rp_related(text)
  - _categorize(text)
  - _extract_text(content)
  - parse_conversations(data, rp_only)
  - main() — file I/O
"""
from __future__ import annotations

import json

from scripts.import_chatgpt_history import (
    _categorize,
    _extract_text,
    _is_rp_related,
    parse_conversations,
    main,
)


# ── _is_rp_related ────────────────────────────────────────────────────────────

def test_is_rp_related_keyword_match():
    assert _is_rp_related("Continue the story of Aurora and the dragon") is True


def test_is_rp_related_yokai_match():
    assert _is_rp_related("This is a Yokai RPG scene with dice roll") is True


def test_is_rp_related_false():
    assert _is_rp_related("What is the capital of France?") is False


def test_is_rp_related_case_insensitive():
    assert _is_rp_related("ROLEPLAY session beginning") is True


# ── _categorize ───────────────────────────────────────────────────────────────

def test_categorize_translation():
    assert _categorize("Please translate this sentence from Italian to English") == "translation"


def test_categorize_brainstorming():
    assert _categorize("I have an idea: what if the guild leader is actually a spy?") == "brainstorming"


def test_categorize_lore():
    # "lore" keyword hits before "describe/write/draft" keywords
    assert _categorize("Tell me about the religion and the geography of this world") == "lore"


def test_categorize_general():
    assert _categorize("Hello, how are you doing today?") == "general"


# ── _extract_text ─────────────────────────────────────────────────────────────

def test_extract_text_string_parts():
    content = {"parts": ["Hello", " world"]}
    assert _extract_text(content) == "Hello\n world"


def test_extract_text_dict_parts():
    content = {"parts": [{"text": "Aurora speaks"}, {"text": "softly"}]}
    assert _extract_text(content) == "Aurora speaks\nsoftly"


def test_extract_text_mixed_parts():
    content = {"parts": ["First", {"text": "Second"}]}
    assert _extract_text(content) == "First\nSecond"


def test_extract_text_none():
    assert _extract_text(None) == ""


def test_extract_text_empty_parts():
    assert _extract_text({"parts": []}) == ""


# ── parse_conversations ───────────────────────────────────────────────────────

def _make_conv(role: str, text: str, title: str = "Test", conv_id: str = "c1") -> dict:
    return {
        "id": conv_id,
        "title": title,
        "create_time": 1700000000,
        "mapping": {
            "node-1": {
                "message": {
                    "author": {"role": role},
                    "content": {"parts": [text]},
                    "create_time": 1700000001,
                }
            }
        },
    }


def test_parse_conversations_basic():
    data = [_make_conv("user", "Continue the scene with Aurora")]
    records = parse_conversations(data)
    assert len(records) == 1
    assert records[0]["role"] == "user"
    assert records[0]["source"] == "chatgpt"
    assert records[0]["rp_related"] is True


def test_parse_conversations_system_role_skipped():
    data = [_make_conv("system", "You are a helpful assistant")]
    records = parse_conversations(data)
    assert len(records) == 0


def test_parse_conversations_too_short_skipped():
    data = [_make_conv("user", "ok")]
    records = parse_conversations(data)
    assert len(records) == 0


def test_parse_conversations_rp_only_filter():
    data = [
        _make_conv("user", "Continue the roleplay scene with Aurora the mage", conv_id="rp"),
        _make_conv("user", "What is the capital of France? Really just asking here.", conv_id="not-rp"),
    ]
    records_all = parse_conversations(data, rp_only=False)
    records_rp = parse_conversations(data, rp_only=True)
    assert len(records_all) == 2
    assert len(records_rp) == 1
    assert records_rp[0]["conversation_id"] == "rp"


def test_parse_conversations_category_assigned():
    data = [_make_conv("assistant", "Translate this text from Italian to English for the scene")]
    records = parse_conversations(data)
    assert records[0]["category"] == "translation"


# ── main() — I/O ─────────────────────────────────────────────────────────────

def test_main_missing_input(tmp_path, capsys):
    out = tmp_path / "out.jsonl"
    ret = main(["--input", str(tmp_path / "nonexistent.json"), "--output", str(out)])
    assert ret == 1


def test_main_produces_jsonl(tmp_path):
    convs = [_make_conv("user", "Continue the roleplay scene with Aurora the mage, using magic")]
    inp = tmp_path / "convs.json"
    inp.write_text(json.dumps(convs), encoding="utf-8")
    out = tmp_path / "out.jsonl"
    ret = main(["--input", str(inp), "--output", str(out)])
    assert ret == 0
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["source"] == "chatgpt"
