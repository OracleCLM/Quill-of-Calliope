import sys

import pytest
pytest.importorskip("pandas")
import pandas as pd
import numpy as np

try:
    pd.Series({"_test": "ok"})
    _PANDAS_SERIES_OK = True
except Exception:
    _PANDAS_SERIES_OK = False

from scripts.import_excel_history import normalize_character_name, safe_str, classify_row, ts_to_iso  # noqa: E402

def test_normalize_hp_stripped():
    assert normalize_character_name("Philip 75/100%") == "Philip"

def test_normalize_no_change():
    assert normalize_character_name("Aurora of Winter") == "Aurora of Winter"

def test_normalize_none():
    assert normalize_character_name(None) is None

def test_normalize_empty():
    result = normalize_character_name("")
    assert result == "" or result is None

def test_safe_str_none():
    assert safe_str(None) is None

def test_safe_str_string():
    assert safe_str("hello") == "hello"

def test_safe_str_nan():
    assert safe_str(np.nan) is None

# classify_row: accepts any object with .get() — plain dict works on py3.13 broken pandas

def test_classify_row_ic():
    row = {"player": "Horo", "character": "Aurora", "message": "She walks", "system message": None}
    assert classify_row(row) == "IC"


def test_classify_row_ooc():
    row = {"player": "Horo", "character": None, "message": "(ooc)", "system message": None}
    assert classify_row(row) == "OOC"


def test_classify_row_system():
    row = {"system message": "Server joined", "character": None}
    assert classify_row(row) == "system"

def test_ts_to_iso_none():
    assert ts_to_iso(None) is None

def test_ts_to_iso_valid():
    ts = pd.Timestamp("2024-01-15 10:30:00")
    result = ts_to_iso(ts)
    assert result is not None and "2024" in result


def test_ts_to_iso_exception_returns_str():
    class Bad:
        def __str__(self): return "bad-ts"
    result = ts_to_iso(Bad())
    # pd.Timestamp(Bad()) raises → fallback str(ts)
    assert result == "bad-ts"


# ─────────────────────────────────────────────────────────────────────────────
# Extended tests — _finalize_scene, _sample_messages, write_messages_clean,
# write_operator_corpus, detect_scenes, extract_narrator_messages,
# extract_char_samples, load_and_clean, main()
# Note: pd.DataFrame creation is broken on py3.13/numpy; use MagicMock iterrows.
# ─────────────────────────────────────────────────────────────────────────────

import json  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402

import scripts.import_excel_history as ieh  # noqa: E402


# ── _finalize_scene ───────────────────────────────────────────────────────────

def test_finalize_scene_basic():
    msgs = [
        {"character": "Aurora", "player": "Horo", "timestamp": "2024-01-01T10:00:00Z", "message": "Hello"},
        {"character": "Philip", "player": "Sam", "timestamp": "2024-01-01T10:05:00Z", "message": "World"},
    ]
    scene = ieh._finalize_scene(0, msgs)
    assert scene["scene_idx"] == 0
    assert scene["scene_id"] == "scene_000"
    assert scene["message_count"] == 2
    assert "Aurora" in scene["participants"]
    assert "Philip" in scene["participants"]
    assert "Horo" in scene["players"]
    assert scene["timestamp_start"] == "2024-01-01T10:00:00Z"
    assert scene["timestamp_end"] == "2024-01-01T10:05:00Z"


def test_finalize_scene_excerpt_truncated_at_200():
    long_msg = "A" * 300
    msgs = [{"character": "Alice", "player": "Horo", "timestamp": "T", "message": long_msg}]
    scene = ieh._finalize_scene(1, msgs)
    assert len(scene["first_msg_excerpt"]) <= 200
    assert len(scene["last_msg_excerpt"]) <= 200


def test_finalize_scene_none_message_gives_empty_excerpt():
    msgs = [{"character": "Alice", "player": "Horo", "timestamp": "T", "message": None}]
    scene = ieh._finalize_scene(0, msgs)
    assert scene["first_msg_excerpt"] == ""


def test_finalize_scene_samples_called():
    msgs = [{"character": "X", "player": "P", "timestamp": "T", "message": f"m{i}"} for i in range(10)]
    scene = ieh._finalize_scene(2, msgs)
    assert len(scene["messages_sample"]) == 5  # n=5 default


# ── _sample_messages ──────────────────────────────────────────────────────────

def test_sample_messages_fewer_than_n_returns_all():
    msgs = [{"message": str(i)} for i in range(3)]
    assert ieh._sample_messages(msgs, n=5) == msgs


def test_sample_messages_exactly_n_returns_all():
    msgs = [{"message": str(i)} for i in range(5)]
    assert ieh._sample_messages(msgs, n=5) == msgs


def test_sample_messages_more_than_n_returns_n():
    msgs = [{"message": str(i)} for i in range(20)]
    result = ieh._sample_messages(msgs, n=5)
    assert len(result) == 5
    assert result[0] == msgs[0]  # first element at step 0


# ── write_messages_clean ──────────────────────────────────────────────────────

def test_write_messages_clean_basic(tmp_path):
    row = {
        "row_idx": 0,
        "timestamp": pd.Timestamp("2024-01-01 10:00"),
        "player": "Horo",
        "character": "Aurora",
        "type": "IC",
        "message": "Hello &amp; world",
        "original message": None,
    }
    df = MagicMock()
    df.iterrows.return_value = [(0, row)]
    out = tmp_path / "messages_clean.jsonl"
    count = ieh.write_messages_clean(df, out)
    assert count == 1
    data = json.loads(out.read_text(encoding="utf-8").strip())
    assert data["row_idx"] == 0
    assert data["type"] == "IC"
    assert data["message"] == "Hello & world"  # html.unescape
    assert data["original_message"] is None


def test_write_messages_clean_with_original_message(tmp_path):
    row = {
        "row_idx": 1,
        "timestamp": None,
        "player": None,
        "character": None,
        "type": "OOC",
        "message": "ooc text",
        "original message": "original ooc",
    }
    df = MagicMock()
    df.iterrows.return_value = [(0, row)]
    out = tmp_path / "mc2.jsonl"
    ieh.write_messages_clean(df, out)
    data = json.loads(out.read_text(encoding="utf-8").strip())
    assert data["original_message"] == "original ooc"


# ── write_operator_corpus ─────────────────────────────────────────────────────

def test_write_operator_corpus_horo_ic(tmp_path):
    row = {
        "row_idx": 5,
        "timestamp": pd.Timestamp("2024-01-01"),
        "player": "Horo",
        "character": "Aurora",
        "type": "IC",
        "message": "Test message",
    }
    df = MagicMock()
    mock_subset = MagicMock()
    mock_subset.iterrows.return_value = [(0, row)]
    df.__getitem__.return_value.copy.return_value = mock_subset
    out = tmp_path / "corpus.jsonl"
    count = ieh.write_operator_corpus(df, out)
    assert count == 1
    data = json.loads(out.read_text(encoding="utf-8").strip())
    assert data["player"] == "Horo"
    assert data["type"] == "IC"


def test_write_operator_corpus_empty(tmp_path):
    df = MagicMock()
    mock_subset = MagicMock()
    mock_subset.iterrows.return_value = []
    df.__getitem__.return_value.copy.return_value = mock_subset
    out = tmp_path / "empty_corpus.jsonl"
    count = ieh.write_operator_corpus(df, out)
    assert count == 0


# ── detect_scenes ─────────────────────────────────────────────────────────────

def test_detect_scenes_single_scene_with_enough_msgs():
    rows = [
        {"row_idx": i, "timestamp": pd.Timestamp(f"2024-01-01 10:{i:02d}:00"),
         "player": "Horo", "character": "Aurora", "message": f"msg{i}"}
        for i in range(12)
    ]
    df = MagicMock()
    mock_ic = MagicMock()
    mock_ic.iterrows.return_value = list(enumerate(rows))
    df.__getitem__.return_value.copy.return_value = mock_ic
    scenes = ieh.detect_scenes(df)
    assert len(scenes) == 1
    assert scenes[0]["message_count"] == 12
    assert "Aurora" in scenes[0]["participants"]


def test_detect_scenes_gap_over_30min_splits_two_scenes():
    # rows1: 10:00–10:11, rows2: 10:42–10:53 (31min gap after rows1[-1])
    rows1 = [
        {"row_idx": i, "timestamp": pd.Timestamp(f"2024-01-01 10:{i:02d}:00"),
         "player": "Horo", "character": "Aurora", "message": f"m{i}"}
        for i in range(12)
    ]
    rows2 = [
        {"row_idx": 12 + i, "timestamp": pd.Timestamp(f"2024-01-01 10:{42 + i:02d}:00"),
         "player": "Sam", "character": "Philip", "message": f"m{12 + i}"}
        for i in range(12)
    ]
    df = MagicMock()
    mock_ic = MagicMock()
    mock_ic.iterrows.return_value = list(enumerate(rows1 + rows2))
    df.__getitem__.return_value.copy.return_value = mock_ic
    scenes = ieh.detect_scenes(df)
    assert len(scenes) == 2


def test_detect_scenes_below_min_messages_filtered():
    rows = [
        {"row_idx": i, "timestamp": pd.Timestamp(f"2024-01-01 10:{i:02d}:00"),
         "player": "Horo", "character": "Aurora", "message": f"m{i}"}
        for i in range(5)  # < SCENE_MIN_MESSAGES=10
    ]
    df = MagicMock()
    mock_ic = MagicMock()
    mock_ic.iterrows.return_value = list(enumerate(rows))
    df.__getitem__.return_value.copy.return_value = mock_ic
    scenes = ieh.detect_scenes(df)
    assert len(scenes) == 0


# ── extract_narrator_messages ─────────────────────────────────────────────────

def test_extract_narrator_messages_basic():
    rows = [
        {"message": "The realm shook.", "character": "NARRATOR"},
        {"message": "Another line.", "character": "NARRATOR"},
    ]
    df = MagicMock()
    mock_narr = MagicMock()
    mock_narr.iterrows.return_value = list(enumerate(rows))
    df.__getitem__.return_value.copy.return_value = mock_narr
    msgs = ieh.extract_narrator_messages(df)
    assert len(msgs) == 2
    assert msgs[0] == "The realm shook."


def test_extract_narrator_messages_none_filtered():
    rows = [
        {"message": None},
        {"message": "Real message."},
    ]
    df = MagicMock()
    mock_narr = MagicMock()
    mock_narr.iterrows.return_value = list(enumerate(rows))
    df.__getitem__.return_value.copy.return_value = mock_narr
    msgs = ieh.extract_narrator_messages(df)
    assert len(msgs) == 1


# ── extract_char_samples ──────────────────────────────────────────────────────

def test_extract_char_samples_empty_char_skipped():
    df = MagicMock()
    char_df = df.__getitem__.return_value.copy.return_value
    char_df.__len__ = MagicMock(return_value=0)
    result = ieh.extract_char_samples(df, ["NoSuchChar"], n_sample=5)
    assert result == {}


def test_extract_char_samples_returns_samples():
    df = MagicMock()
    char_df = df.__getitem__.return_value.copy.return_value
    char_df.__len__ = MagicMock(return_value=5)
    mock_combined = MagicMock()
    mock_combined.drop_duplicates.return_value.sort_values.return_value.iterrows.return_value = [
        (0, {"timestamp": pd.Timestamp("2024-01-01"), "player": "Horo", "message": "Hello"}),
    ]
    with patch("scripts.import_excel_history.pd.concat", return_value=mock_combined):
        result = ieh.extract_char_samples(df, ["Aurora"], n_sample=5)
    assert "Aurora" in result
    assert len(result["Aurora"]) == 1
    assert result["Aurora"][0]["message"] == "Hello"


# ── main() ────────────────────────────────────────────────────────────────────

def test_main_missing_xlsx_exits(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path / "missing.xlsx")])
    with pytest.raises(SystemExit) as exc:
        ieh.main()
    assert exc.value.code == 1


def test_main_full_pipeline(monkeypatch, tmp_path, capsys):
    xlsx = tmp_path / "test.xlsx"
    xlsx.touch()
    monkeypatch.setattr(sys, "argv", ["prog", str(xlsx), "--output", str(tmp_path)])
    mock_df = MagicMock()

    with patch("scripts.import_excel_history.load_and_clean", return_value=mock_df), \
         patch("scripts.import_excel_history.write_messages_clean", return_value=32598), \
         patch("scripts.import_excel_history.write_operator_corpus", return_value=100), \
         patch("scripts.import_excel_history.detect_scenes", return_value=[{"scene": 1}]), \
         patch("scripts.import_excel_history.extract_char_samples", return_value={"Aurora": []}), \
         patch("scripts.import_excel_history.extract_narrator_messages", return_value=["msg"]):
        ieh.main()

    captured = capsys.readouterr()
    assert "M1 Phase 1 Complete" in captured.out
    assert "32598" in captured.out
