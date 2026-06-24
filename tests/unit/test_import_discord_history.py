"""Unit test per funzioni pure di scripts/import_discord_history.py."""
from __future__ import annotations

import json

from scripts.import_discord_history import _classify_tag, _load_tupper_names


# ── _classify_tag ─────────────────────────────────────────────────────────────

def test_classify_tag_system_thread_created():
    assert _classify_tag("ThreadCreated", "") == "system"


def test_classify_tag_system_pinned():
    assert _classify_tag("ChannelPinnedMessage", "") == "system"


def test_classify_tag_ooc_parentheses():
    assert _classify_tag("Default", "(OOC comment)") == "OOC"


def test_classify_tag_ooc_brackets():
    assert _classify_tag("Default", "[brackets note]") == "OOC"


def test_classify_tag_ic():
    assert _classify_tag("Default", "Hello world") == "IC"


def test_classify_tag_ooc_leading_space():
    assert _classify_tag("Default", "  (leading space then OOC)") == "OOC"


# ── _load_tupper_names ────────────────────────────────────────────────────────

def test_load_tupper_names_missing_file(tmp_path):
    assert _load_tupper_names(tmp_path / "nonexistent.json") == set()


def test_load_tupper_names_two_tuppers(tmp_path):
    p = tmp_path / "tuppers.json"
    p.write_text(json.dumps({"tuppers": [{"name": "Alice"}, {"name": "Bob"}]}))
    assert _load_tupper_names(p) == {"Alice", "Bob"}


def test_load_tupper_names_empty_list(tmp_path):
    p = tmp_path / "tuppers.json"
    p.write_text(json.dumps({"tuppers": []}))
    assert _load_tupper_names(p) == set()


def test_load_tupper_names_invalid_json(tmp_path):
    p = tmp_path / "tuppers.json"
    p.write_text("not json")
    assert _load_tupper_names(p) == set()
