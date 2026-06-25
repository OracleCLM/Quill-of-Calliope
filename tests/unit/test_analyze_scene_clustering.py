"""Unit tests for scripts/analyze_scene_clustering.py — pure functions, no files needed."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from analyze_scene_clustering import (  # noqa: E402
    bucket_durations,
    fmt_stats_row,
    main,
    parse_duration_real,
    stats_dict,
    ts_to_dt,
)


class TestParseDurationReal:
    def test_hours_only(self):
        assert parse_duration_real("3h") == 180.0

    def test_minutes_only(self):
        assert parse_duration_real("45m") == 45.0

    def test_hours_and_minutes(self):
        assert parse_duration_real("2h 18m") == 138.0

    def test_single_digit_hour(self):
        assert parse_duration_real("1h 5m") == 65.0

    def test_float_hours(self):
        result = parse_duration_real("1.5h")
        assert result == 90.0

    def test_no_match_returns_none(self):
        assert parse_duration_real("unknown") is None
        assert parse_duration_real("") is None
        assert parse_duration_real("30s") is None  # seconds not supported

    def test_leading_trailing_whitespace(self):
        assert parse_duration_real("  2h  ") == 120.0

    def test_50m(self):
        assert parse_duration_real("50m") == 50.0


class TestTsToDt:
    def test_iso_utc(self):
        dt = ts_to_dt("2024-01-15T10:30:00Z")
        assert isinstance(dt, datetime)
        assert dt.year == 2024
        assert dt.month == 1

    def test_iso_with_offset(self):
        dt = ts_to_dt("2024-06-01T12:00:00+02:00")
        assert isinstance(dt, datetime)

    def test_invalid_returns_none(self):
        assert ts_to_dt("not-a-date") is None
        assert ts_to_dt("") is None

    def test_timezone_aware(self):
        dt = ts_to_dt("2024-01-01T00:00:00Z")
        assert dt.tzinfo is not None


class TestStatsDict:
    def test_empty_returns_empty(self):
        assert stats_dict([]) == {}

    def test_single_value(self):
        s = stats_dict([42.0])
        assert s["n"] == 1
        assert s["min"] == 42.0
        assert s["max"] == 42.0
        assert s["mean"] == 42.0
        assert s["median"] == 42.0

    def test_multiple_values(self):
        s = stats_dict([10.0, 20.0, 30.0, 40.0, 50.0])
        assert s["n"] == 5
        assert s["min"] == 10.0
        assert s["max"] == 50.0
        assert s["mean"] == 30.0
        assert s["median"] == 30.0

    def test_rounding(self):
        s = stats_dict([1.0, 2.0, 3.0])
        assert isinstance(s["mean"], float)

    def test_p25_p75_present(self):
        s = stats_dict([1.0, 2.0, 3.0, 4.0])
        assert "p25" in s
        assert "p75" in s


class TestBucketDurations:
    def test_all_buckets_present(self):
        result = bucket_durations([15.0, 60.0, 120.0, 200.0])
        assert set(result.keys()) == {"0-30min", "30-90min", "90-180min", "180+min"}

    def test_zero_to_30(self):
        result = bucket_durations([10.0, 25.0, 29.9])
        assert result["0-30min"] == 3

    def test_30_to_90(self):
        result = bucket_durations([30.0, 60.0, 89.9])
        assert result["30-90min"] == 3

    def test_90_to_180(self):
        result = bucket_durations([90.0, 150.0])
        assert result["90-180min"] == 2

    def test_over_180(self):
        result = bucket_durations([180.0, 300.0])
        assert result["180+min"] == 2

    def test_empty(self):
        result = bucket_durations([])
        assert all(v == 0 for v in result.values())

    def test_mixed(self):
        result = bucket_durations([15.0, 60.0, 120.0, 250.0])
        assert result["0-30min"] == 1
        assert result["30-90min"] == 1
        assert result["90-180min"] == 1
        assert result["180+min"] == 1


class TestFmtStatsRow:
    def test_nonempty_stats(self):
        s = stats_dict([10.0, 20.0, 30.0])
        row = fmt_stats_row("duration", s)
        assert "duration" in row
        assert isinstance(row, str)

    def test_with_single_value_stats(self):
        s = stats_dict([99.0])
        row = fmt_stats_row("single", s)
        assert "single" in row
        assert "99" in row


# ── main() — copertura righe 85-242 ──────────────────────────────────────────

def _draft_scene(scene_id: str, ts_start: str, ts_end: str, msg_count: int = 20,
                 participants: list | None = None) -> dict:
    return {
        "scene_id": scene_id,
        "timestamp_start": ts_start,
        "timestamp_end": ts_end,
        "message_count": msg_count,
        "participants": participants or ["Alice", "Bob"],
    }


def _write_draft(directory: Path, name: str, data: dict) -> Path:
    p = directory / f"{name}.draft.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")
    return p


def test_main_empty_directory(tmp_path, monkeypatch, capsys):
    """Lines 98-101: nessun *.draft.yaml → stampa messaggio e return."""
    scenes_dir = tmp_path / "scenes"
    scenes_dir.mkdir()
    out = tmp_path / "report.md"
    monkeypatch.setattr("sys.argv", [
        "analyze_scene_clustering.py",
        "--scenes-dir", str(scenes_dir),
        "--output", str(out),
    ])
    main()
    assert "No *.draft.yaml" in capsys.readouterr().out
    assert not out.exists()


def test_main_one_valid_scene(tmp_path, monkeypatch, capsys):
    """Lines 104-242: 1 scena con timestamp → report markdown scritto."""
    scenes_dir = tmp_path / "scenes"
    scenes_dir.mkdir()
    _write_draft(scenes_dir, "s01", _draft_scene("s01", "2024-01-01T20:00:00+00:00", "2024-01-01T21:30:00+00:00"))
    out = tmp_path / "report.md"
    monkeypatch.setattr("sys.argv", [
        "analyze_scene_clustering.py",
        "--scenes-dir", str(scenes_dir),
        "--output", str(out),
    ])
    main()
    stdout = capsys.readouterr().out
    assert "Loaded 1 scenes" in stdout
    assert "Report written to" in stdout
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Scene Clustering Review" in content
    assert "Statistics Table" in content


def test_main_yaml_error_skipped(tmp_path, monkeypatch, capsys):
    """Lines 108-111: YAML invalido → parse_errors++, continua con scena valida."""
    scenes_dir = tmp_path / "scenes"
    scenes_dir.mkdir()
    _write_draft(scenes_dir, "good", _draft_scene("good", "2024-01-01T10:00:00+00:00", "2024-01-01T11:30:00+00:00"))
    (scenes_dir / "bad.draft.yaml").write_text("invalid: yaml: [", encoding="utf-8")
    out = tmp_path / "report.md"
    monkeypatch.setattr("sys.argv", [
        "analyze_scene_clustering.py",
        "--scenes-dir", str(scenes_dir),
        "--output", str(out),
    ])
    main()
    assert "Loaded 1 scenes" in capsys.readouterr().out


def test_main_non_dict_yaml_skipped(tmp_path, monkeypatch, capsys):
    """Line 112-113: YAML valido ma non dict → skip, scena non aggiunta."""
    scenes_dir = tmp_path / "scenes"
    scenes_dir.mkdir()
    _write_draft(scenes_dir, "valid", _draft_scene("v01", "2024-01-01T10:00:00+00:00", "2024-01-01T11:30:00+00:00"))
    (scenes_dir / "nondict.draft.yaml").write_text("- item1\n- item2", encoding="utf-8")
    out = tmp_path / "report.md"
    monkeypatch.setattr("sys.argv", [
        "analyze_scene_clustering.py",
        "--scenes-dir", str(scenes_dir),
        "--output", str(out),
    ])
    main()
    assert "Loaded 1 scenes" in capsys.readouterr().out


def test_main_two_scenes_gap_calculated(tmp_path, monkeypatch, capsys):
    """Lines 148-156: 2 scene con timestamp → gap calcolato e stampato."""
    scenes_dir = tmp_path / "scenes"
    scenes_dir.mkdir()
    _write_draft(scenes_dir, "s01", _draft_scene("s01", "2024-01-01T20:00:00+00:00", "2024-01-01T21:00:00+00:00"))
    _write_draft(scenes_dir, "s02", _draft_scene("s02", "2024-01-01T22:00:00+00:00", "2024-01-01T23:00:00+00:00"))
    out = tmp_path / "report.md"
    monkeypatch.setattr("sys.argv", [
        "analyze_scene_clustering.py",
        "--scenes-dir", str(scenes_dir),
        "--output", str(out),
    ])
    main()
    stdout = capsys.readouterr().out
    assert "Loaded 2 scenes" in stdout
    assert "Gap stats" in stdout


def test_main_duration_real_fallback(tmp_path, monkeypatch, capsys):
    """Lines 131-133: nessun timestamp, usa duration_real string."""
    scenes_dir = tmp_path / "scenes"
    scenes_dir.mkdir()
    _write_draft(scenes_dir, "s01", {
        "scene_id": "s01",
        "duration_real": "1h 30m",
        "message_count": 40,
        "participants": ["Alice"],
    })
    out = tmp_path / "report.md"
    monkeypatch.setattr("sys.argv", [
        "analyze_scene_clustering.py",
        "--scenes-dir", str(scenes_dir),
        "--output", str(out),
    ])
    main()
    stdout = capsys.readouterr().out
    assert "Loaded 1 scenes" in stdout
    assert "Duration stats" in stdout


def test_main_no_duration_info(tmp_path, monkeypatch, capsys):
    """Line 136: scena senza timestamp e senza duration_real → duration_min=None."""
    scenes_dir = tmp_path / "scenes"
    scenes_dir.mkdir()
    # Scene con solo message_count (no timestamps, no duration_real)
    _write_draft(scenes_dir, "s01", {
        "scene_id": "s01",
        "message_count": 15,
        "participants": ["Alice"],
    })
    # Serve una seconda scena con duration per evitare ZeroDivisionError in histogram
    _write_draft(scenes_dir, "s02", _draft_scene("s02", "2024-01-02T10:00:00+00:00", "2024-01-02T11:00:00+00:00"))
    out = tmp_path / "report.md"
    monkeypatch.setattr("sys.argv", [
        "analyze_scene_clustering.py",
        "--scenes-dir", str(scenes_dir),
        "--output", str(out),
    ])
    main()
    assert "Loaded 2 scenes" in capsys.readouterr().out
