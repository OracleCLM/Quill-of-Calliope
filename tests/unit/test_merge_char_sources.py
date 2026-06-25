"""Unit test per scripts/merge_char_sources.py (base zai-glm, fix Claude)."""
from __future__ import annotations

from datetime import timezone

from scripts.merge_char_sources import _parse_dt, _prefix_word_match, slugify


# ── slugify ───────────────────────────────────────────────────────────────────

def test_slugify_basic():
    assert slugify("Hello World") == "hello-world"


def test_slugify_unicode_kept():
    # \w mantiene caratteri unicode (é non rimosso)
    assert slugify("Café au Lait") == "café-au-lait"


def test_slugify_special_chars_removed_no_separator():
    # !@# rimossi, ma nessuno spazio tra hello e world → helloworld
    assert slugify("Hello!@#World") == "helloworld"


def test_slugify_underscores_to_hyphen():
    assert slugify("hello_world") == "hello-world"


def test_slugify_strip_leading_trailing():
    assert slugify("  -test- ") == "test"


def test_slugify_multiple_spaces_collapsed():
    assert slugify("a   b") == "a-b"


def test_slugify_empty():
    assert slugify("") == ""


# ── _prefix_word_match ─────────────────────────────────────────────────────────

def test_prefix_match_exact():
    assert _prefix_word_match("Aurora", ["Aurora"]) == "Aurora"


def test_prefix_match_name_starts_with_candidate():
    assert _prefix_word_match("Aurora of Winter", ["Aurora"]) == "Aurora"


def test_prefix_match_hyphen_boundary():
    assert _prefix_word_match("Jean-Luc", ["Jean"]) == "Jean"


def test_prefix_match_quote_boundary():
    assert _prefix_word_match("Luke's Hand", ["Luke"]) == "Luke"


def test_prefix_match_candidate_starts_with_name():
    assert _prefix_word_match("Aurora", ["Aurora of Winter"]) == "Aurora of Winter"


def test_prefix_match_no_match():
    assert _prefix_word_match("Bob", ["Alice"]) is None


def test_prefix_match_no_word_boundary():
    # "Aurorax" starts with "Aurora" but next char is 'x', not boundary
    assert _prefix_word_match("Aurorax", ["Aurora"]) is None


def test_prefix_match_empty_candidate_skipped():
    assert _prefix_word_match("Test", ["", "Test"]) == "Test"


def test_prefix_match_case_insensitive():
    assert _prefix_word_match("aurora", ["AURORA"]) == "AURORA"


# ── _parse_dt ─────────────────────────────────────────────────────────────────

def test_parse_dt_none():
    assert _parse_dt(None) is None


def test_parse_dt_empty_string():
    assert _parse_dt("") is None


def test_parse_dt_z_suffix():
    dt = _parse_dt("2023-01-01T12:00:00Z")
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.year == 2023


def test_parse_dt_with_offset():
    dt = _parse_dt("2023-01-01T12:00:00+02:00")
    assert dt is not None
    assert dt.tzinfo is not None


def test_parse_dt_naive_gets_utc():
    dt = _parse_dt("2023-01-01T12:00:00")
    assert dt is not None
    assert dt.tzinfo == timezone.utc


def test_parse_dt_invalid_returns_none():
    assert _parse_dt("not-a-date") is None


# ── fuzzy_match_chars ─────────────────────────────────────────────────────────

import json  # noqa: E402
from datetime import datetime  # noqa: E402
from pathlib import Path  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402

import pytest  # noqa: E402
import yaml  # noqa: E402

import scripts.merge_char_sources as mcs  # noqa: E402


def test_fuzzy_match_alias_map_hit_in_candidates():
    alias_map = {"alice": "Alice Smith"}
    result = mcs.fuzzy_match_chars("alice", ["Alice Smith", "Bob"], alias_map=alias_map)
    assert result == "Alice Smith"


def test_fuzzy_match_alias_map_hit_not_in_candidates():
    alias_map = {"alice": "Alice Smith"}
    result = mcs.fuzzy_match_chars("alice", ["Bob"], alias_map=alias_map)
    assert result == "Alice Smith"


def test_fuzzy_match_prefix_word_boundary():
    # "Alice" prefix-matches "Alice Smith" at space boundary
    result = mcs.fuzzy_match_chars("Alice", ["Alice Smith", "Bob"])
    assert result == "Alice Smith"


def test_fuzzy_match_sequencematcher_fallback():
    # "Alic" is close enough to "Alice Smith" with threshold=0.5
    result = mcs.fuzzy_match_chars("Alic", ["Alice Smith", "Bob"], threshold=0.5)
    assert result == "Alice Smith"


def test_fuzzy_match_no_match():
    result = mcs.fuzzy_match_chars("Charlie", ["Alice Smith", "Bob"], threshold=0.9)
    assert result is None


# ── load_tuppers ──────────────────────────────────────────────────────────────

def test_load_tuppers_valid(tmp_path):
    p = tmp_path / "tuppers.json"
    p.write_text(json.dumps({"tuppers": [{"name": "Alice"}]}))
    assert mcs.load_tuppers(str(p)) == [{"name": "Alice"}]


def test_load_tuppers_missing_key(tmp_path):
    p = tmp_path / "tuppers.json"
    p.write_text(json.dumps({"other": []}))
    assert mcs.load_tuppers(str(p)) == []


# ── load_discord_sheets ───────────────────────────────────────────────────────

def test_load_discord_sheets_not_exists(tmp_path):
    assert mcs.load_discord_sheets(str(tmp_path / "missing.jsonl")) == []


def test_load_discord_sheets_valid(tmp_path):
    p = tmp_path / "sheets.jsonl"
    p.write_text('{"char_name": "Alice"}\n  \n{"char_name": "Bob"}')
    result = mcs.load_discord_sheets(str(p))
    assert result == [{"char_name": "Alice"}, {"char_name": "Bob"}]


# ── load_corpus_samples ───────────────────────────────────────────────────────

def test_load_corpus_samples_not_exists(tmp_path):
    assert mcs.load_corpus_samples(str(tmp_path / "missing.jsonl")) == {}


def test_load_corpus_samples_valid(tmp_path):
    p = tmp_path / "corpus.jsonl"
    p.write_text(
        '{"character": "Alice", "message": "Hi", "timestamp": "2023-01-02T00:00:00Z"}\n'
        '{"character": "Alice", "message": "Hello", "timestamp": "2023-01-01T00:00:00Z"}\n'
        '{"character": "Bob", "message": "Hey", "timestamp": "2023-01-03T00:00:00Z"}'
    )
    result = mcs.load_corpus_samples(str(p), max_per_char=1)
    assert result["Alice"]["messages"] == ["Hi"]
    assert result["Alice"]["last_ts"] == "2023-01-02T00:00:00Z"
    assert "Bob" in result


def test_load_corpus_samples_truncation(tmp_path):
    p = tmp_path / "corpus.jsonl"
    lines = [
        f'{{"character": "A", "message": "m{i}", "timestamp": "2023-01-{i:02d}T00:00:00Z"}}'
        for i in range(1, 60)
    ]
    p.write_text("\n".join(lines))
    result = mcs.load_corpus_samples(str(p), max_per_char=50)
    assert len(result["A"]["messages"]) == 50


def test_load_corpus_samples_skips_missing_char_or_msg(tmp_path):
    p = tmp_path / "corpus.jsonl"
    p.write_text(
        '{"character": "", "message": "Hi", "timestamp": "2023-01-01T00:00:00Z"}\n'
        '{"character": "Alice", "message": "", "timestamp": "2023-01-01T00:00:00Z"}\n'
        '{"character": "Alice", "message": "Good", "timestamp": "2023-01-02T00:00:00Z"}'
    )
    result = mcs.load_corpus_samples(str(p))
    assert list(result.keys()) == ["Alice"]
    assert result["Alice"]["messages"] == ["Good"]


# ── llm_intelligent_merge ─────────────────────────────────────────────────────

@patch("scripts.merge_char_sources.requests.post")
def test_llm_intelligent_merge_success(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"content": "Merged content"}
    mock_post.return_value = mock_resp
    result = mcs.llm_intelligent_merge("Tupper", "Sheet")
    assert result == "Merged content"


@patch("scripts.merge_char_sources.requests.post")
def test_llm_intelligent_merge_empty_content_fallback(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"content": "   "}
    mock_post.return_value = mock_resp
    result = mcs.llm_intelligent_merge("Short", "Longer description here")
    assert result == "Longer description here"


@patch("scripts.merge_char_sources.requests.post")
def test_llm_intelligent_merge_exception_fallback(mock_post):
    mock_post.side_effect = Exception("Network error")
    result = mcs.llm_intelligent_merge("Short", "Longer description here")
    assert result == "Longer description here"


# ── merge_char ────────────────────────────────────────────────────────────────

def test_merge_char_neither_raises():
    with pytest.raises(ValueError):
        mcs.merge_char(None, None, {})


def test_merge_char_tupper_only():
    tupper = {"name": "Alice", "description": "Tupper Desc", "author_id": "123"}
    result = mcs.merge_char(tupper, None, {})
    assert result["name"] == "Alice"
    assert result["physical"] == "Tupper Desc"
    assert result["lore"] == "Tupper Desc"
    assert result["author_id"] == "123"
    assert result["metadata"]["physical"]["source"] == "tupperbox"


def test_merge_char_sheet_only():
    sheet = {"char_name": "Bob", "sheet_text": "Sheet Text", "author_id": "456"}
    result = mcs.merge_char(None, sheet, {})
    assert result["name"] == "Bob"
    assert result["physical"] == "Sheet Text"
    assert result["lore"] == "Sheet Text"
    assert result["metadata"]["physical"]["source"] == "discord-thread"


def test_merge_char_both_sheet_newer_by_180():
    dt_old = datetime(2023, 1, 1, tzinfo=timezone.utc)
    dt_new = datetime(2023, 8, 1, tzinfo=timezone.utc)  # 211 days gap
    tupper = {"name": "A", "description": "Old T", "last_used": dt_old.isoformat()}
    sheet = {"char_name": "A", "sheet_text": "New S", "last_updated": dt_new.isoformat()}
    result = mcs.merge_char(tupper, sheet, {})
    assert result["deprecated_physical_v1"] == "Old T"
    assert result["physical"] == "New S"
    assert result["metadata"]["physical"]["source"] == "discord-thread"


def test_merge_char_both_tupper_newer_by_180():
    dt_old = datetime(2023, 1, 1, tzinfo=timezone.utc)
    dt_new = datetime(2023, 8, 1, tzinfo=timezone.utc)
    tupper = {"name": "A", "description": "New T", "last_used": dt_new.isoformat()}
    sheet = {"char_name": "A", "sheet_text": "Old S", "last_updated": dt_old.isoformat()}
    result = mcs.merge_char(tupper, sheet, {})
    assert result["deprecated_physical_v1"] == "Old S"
    assert result["physical"] == "New T"
    assert result["metadata"]["physical"]["source"] == "tupperbox"


def test_merge_char_both_close_dates_with_llm():
    dt1 = datetime(2023, 1, 1, tzinfo=timezone.utc)
    dt2 = datetime(2023, 2, 1, tzinfo=timezone.utc)  # 31 days gap
    tupper = {"name": "A", "description": "T", "last_used": dt1.isoformat()}
    sheet = {"char_name": "A", "sheet_text": "S", "last_updated": dt2.isoformat()}
    mock_merge = MagicMock(return_value="Merged Result")
    result = mcs.merge_char(tupper, sheet, {}, llm_merge_fn=mock_merge)
    assert result["physical"] == "Merged Result"
    mock_merge.assert_called_once()


def test_merge_char_both_close_dates_llm_raises():
    dt1 = datetime(2023, 1, 1, tzinfo=timezone.utc)
    dt2 = datetime(2023, 2, 1, tzinfo=timezone.utc)
    tupper = {"name": "A", "description": "T", "last_used": dt1.isoformat()}
    sheet = {"char_name": "A", "sheet_text": "S", "last_updated": dt2.isoformat()}
    mock_merge = MagicMock(side_effect=Exception("LLM Fail"))
    result = mcs.merge_char(tupper, sheet, {}, llm_merge_fn=mock_merge)
    assert result["physical"] == "T"


def test_merge_char_both_close_dates_no_llm():
    dt1 = datetime(2023, 1, 1, tzinfo=timezone.utc)
    dt2 = datetime(2023, 2, 1, tzinfo=timezone.utc)
    tupper = {"name": "A", "description": "T", "last_used": dt1.isoformat()}
    sheet = {"char_name": "A", "sheet_text": "S", "last_updated": dt2.isoformat()}
    result = mcs.merge_char(tupper, sheet, {})
    assert result["physical"] == "T"
    assert "deprecated_physical_v1" not in result


def test_merge_char_missing_dates_tupper_fallback():
    tupper = {"name": "A", "description": "T"}
    sheet = {"char_name": "A", "sheet_text": "S"}
    result = mcs.merge_char(tupper, sheet, {})
    assert result["physical"] == "T"
    assert "deprecated_physical_v1" not in result


def test_merge_char_thread_id_in_metadata():
    sheet = {"char_name": "A", "sheet_text": "S", "thread_id": "12345"}
    result = mcs.merge_char(None, sheet, {})
    assert result["metadata"]["lore"]["thread_id"] == "12345"
    assert result["metadata"]["physical"]["thread_id"] == "12345"


def test_merge_char_voice_samples():
    samples = {"messages": ["msg1", "msg2"], "last_ts": "2023-01-01T10:00:00Z"}
    tupper = {"name": "A", "description": "T"}
    result = mcs.merge_char(tupper, None, samples)
    assert result["voice_samples"] == ["msg1", "msg2"]
    assert result["metadata"]["voice"]["last_msg"] == "2023-01-01"
    assert result["metadata"]["voice"]["sample_count"] == 2


# ── load_alias_map ────────────────────────────────────────────────────────────

def test_load_alias_map_not_exists(tmp_path):
    assert mcs.load_alias_map(str(tmp_path / "missing.yaml")) == {}


def test_load_alias_map_none():
    assert mcs.load_alias_map(None) == {}


def test_load_alias_map_valid(tmp_path):
    p = tmp_path / "aliases.yaml"
    p.write_text("Alice: Alice Smith\nBob: Robert")
    result = mcs.load_alias_map(str(p))
    assert result["alice"] == "Alice Smith"
    assert result["bob"] == "Robert"


# ── merge_all ─────────────────────────────────────────────────────────────────

def test_merge_all_basic(tmp_path):
    tuppers = [{"name": "Alice", "description": "Desc Alice"}]
    sheets = [{"char_name": "Bob", "sheet_text": "Desc Bob"}]
    out_dir = tmp_path / "out"
    result = mcs.merge_all(tuppers, sheets, {}, str(out_dir))
    assert len(result) == 2
    names = {r["name"] for r in result}
    assert names == {"Alice", "Bob"}
    assert (out_dir / "alice.yaml").exists()
    assert (out_dir / "bob.yaml").exists()


def test_merge_all_error_handling(tmp_path, capsys):
    tupper = {"name": "Alice"}
    out_dir = tmp_path / "out"
    with patch("scripts.merge_char_sources.merge_char", side_effect=ValueError("Test error")):
        result = mcs.merge_all([tupper], [], {}, str(out_dir))
    assert result == []
    assert "Error merging 'Alice'" in capsys.readouterr().err


def test_merge_all_corpus_match(tmp_path):
    tuppers = [{"name": "Alice", "description": "Desc"}]
    corpus = {"Alice": {"messages": ["hello"], "last_ts": "2023-01-01T00:00:00Z"}}
    out_dir = tmp_path / "out"
    result = mcs.merge_all(tuppers, [], corpus, str(out_dir))
    assert result[0]["voice_samples"] == ["hello"]


# ── main() ────────────────────────────────────────────────────────────────────

def test_main_full_flow(tmp_path, monkeypatch, capsys):
    # Use clearly distinct names to avoid fuzzy-matching each other
    t_file = tmp_path / "t.json"
    t_file.write_text(json.dumps({"tuppers": [{"name": "Alice", "description": "D1"}]}))
    s_file = tmp_path / "s.jsonl"
    s_file.write_text('{"char_name": "Zephyr", "sheet_text": "D2"}')
    c_file = tmp_path / "c.jsonl"
    c_file.write_text('{"character": "Alice", "message": "Hi", "timestamp": "2023-01-01T00:00:00Z"}')
    out_dir = tmp_path / "output"
    monkeypatch.setattr("sys.argv", [
        "script",
        "--tuppers", str(t_file),
        "--discord-sheets", str(s_file),
        "--excel-samples", str(c_file),
        "--output", str(out_dir),
    ])
    mcs.main()
    captured = capsys.readouterr()
    assert "Merged 2 characters" in captured.out
    assert (out_dir / "alice.yaml").exists()
    assert (out_dir / "zephyr.yaml").exists()
    c1 = yaml.safe_load((out_dir / "alice.yaml").read_text())
    assert c1["voice_samples"] == ["Hi"]


def test_main_dry_run(tmp_path, monkeypatch, capsys):
    import shutil
    t_file = tmp_path / "t.json"
    t_file.write_text(json.dumps({"tuppers": [{"name": "TestChar", "description": "D"}]}))
    s_file = tmp_path / "s.jsonl"
    s_file.write_text("")
    c_file = tmp_path / "c.jsonl"
    c_file.write_text("")
    monkeypatch.setattr("sys.argv", [
        "script",
        "--tuppers", str(t_file),
        "--discord-sheets", str(s_file),
        "--excel-samples", str(c_file),
        "--output", str(tmp_path / "out"),
        "--dry-run",
    ])
    try:
        mcs.main()
        captured = capsys.readouterr()
        assert "Merged 1 characters" in captured.out
        assert Path("/tmp/char_merge_test/testchar.yaml").exists()
    finally:
        shutil.rmtree("/tmp/char_merge_test", ignore_errors=True)
