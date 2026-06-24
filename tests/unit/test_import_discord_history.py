"""Unit test per funzioni pure di scripts/import_discord_history.py."""
from __future__ import annotations

import json
from unittest.mock import patch

import yaml

from scripts.import_discord_history import (
    _apply_player_status,
    _classify_tag,
    _load_player_index,
    _load_tupper_names,
    main,
)


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


# ── coverage gaps: _load_player_index + _apply_player_status + main() ─────────

def test_load_player_index_missing_file(tmp_path):
    result = _load_player_index(tmp_path / "missing.yaml")
    assert result is None


def test_load_player_index_valid(tmp_path):
    p = tmp_path / "players.yaml"
    p.write_text(yaml.dump({
        "players": [
            {"name": "Alice", "aliases": ["Allie"]},
            {"name": "Bob", "aliases": []},
        ]
    }), encoding="utf-8")
    result = _load_player_index(p)
    assert result is not None
    assert len(result["candidates"]) == 3


def test_load_player_index_exception_returns_none(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("not: valid: yaml: :", encoding="utf-8")
    with patch("scripts.import_discord_history._yaml.safe_load", side_effect=RuntimeError("bad")):
        result = _load_player_index(p)
    assert result is None


def test_apply_player_status_none_index():
    rec = {"author_name": "Alice"}
    result = _apply_player_status(rec, None)
    assert result["player_status"] is None
    assert result["player_match_name"] is None


def test_apply_player_status_match_found(tmp_path):
    p = tmp_path / "players.yaml"
    p.write_text(yaml.dump({"players": [{"name": "Alice", "aliases": []}]}), encoding="utf-8")
    index = _load_player_index(p)
    rec = {"author_name": "Alice", "author_nick": None}
    result = _apply_player_status(rec, index)
    assert result["player_status"] == "active"
    assert result["player_match_name"] == "Alice"


def test_apply_player_status_no_match(tmp_path):
    p = tmp_path / "players.yaml"
    p.write_text(yaml.dump({"players": [{"name": "Alice", "aliases": []}]}), encoding="utf-8")
    index = _load_player_index(p)
    rec = {"author_name": "Completely_Different_Name_XYZ99", "author_nick": None}
    result = _apply_player_status(rec, index)
    assert result["player_status"] == "unknown"
    assert result["player_match_name"] is None


def _dce_channel(msgs=None):
    return {
        "guild": {"id": "g1", "name": "Test Guild"},
        "channel": {"id": "c1", "type": "GuildTextChat", "name": "general"},
        "messages": msgs or [],
    }


def _dce_msg(msg_id="m1", content="Hello", is_bot=False):
    return {
        "id": msg_id,
        "timestamp": "2024-01-01T10:00:00+00:00",
        "timestampEdited": None,
        "type": "Default",
        "content": content,
        "author": {"id": "u1", "name": "User", "isBot": is_bot},
        "attachments": [],
        "reactions": [],
    }


def test_main_invalid_input_dir_returns_1(tmp_path):
    ret = main(["--input-dir", str(tmp_path / "nonexistent"), "--output", str(tmp_path / "out.jsonl")])
    assert ret == 1


def test_main_empty_input_dir_returns_0(tmp_path):
    ret = main(["--input-dir", str(tmp_path), "--output", str(tmp_path / "out.jsonl")])
    assert ret == 0


def test_main_successful_import(tmp_path):
    data = _dce_channel([_dce_msg("m1", "Hello")])
    (tmp_path / "ch1.json").write_text(json.dumps(data), encoding="utf-8")
    out = tmp_path / "out.jsonl"
    ret = main(["--input-dir", str(tmp_path), "--output", str(out)])
    assert ret == 0
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["message_id"] == "m1"


def test_main_skips_corrupt_json(tmp_path):
    (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
    out = tmp_path / "out.jsonl"
    ret = main(["--input-dir", str(tmp_path), "--output", str(out)])
    assert ret == 0


def test_parse_channel_thread_sets_parent_channel_id():
    """Line 128: channel_type=GuildPublicThread → parent_channel_id impostato."""
    from scripts.import_discord_history import parse_channel
    data = {
        "guild": {"id": "g1", "name": "Guild"},
        "channel": {"id": "c1", "type": "GuildPublicThread", "name": "thread", "categoryId": "parent-c"},
        "messages": [_dce_msg("m1")],
    }
    records = parse_channel(data, set())
    assert records[0]["parent_channel_id"] == "parent-c"


def test_main_no_player_index_logs_null(tmp_path):
    """Line 233: nessun player index → log 'null' (branch else)."""
    data = _dce_channel([_dce_msg("m1")])
    (tmp_path / "ch1.json").write_text(json.dumps(data), encoding="utf-8")
    out = tmp_path / "out.jsonl"
    ret = main([
        "--input-dir", str(tmp_path),
        "--output", str(out),
        "--players-yaml", str(tmp_path / "nonexistent.yaml"),
    ])
    assert ret == 0
