"""Unit tests for scripts/analyze_scene_clustering.py — pure functions, no files needed."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from analyze_scene_clustering import (  # noqa: E402
    bucket_durations,
    fmt_stats_row,
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
