"""GAP-48: test unitari per helper puri in import_routes — _filter_by_span, _channel_meta, _safe_resolve."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.import_routes import _channel_meta, _filter_by_span, _safe_resolve


# ── _filter_by_span ───────────────────────────────────────────────────────────


def test_filter_no_bounds_returns_all():
    records = [{"timestamp": "2024-01-01"}, {"timestamp": "2024-06-01"}]
    assert _filter_by_span(records, None, None) == records


def test_filter_since_excludes_older():
    records = [
        {"timestamp": "2024-01-01T10:00:00"},
        {"timestamp": "2024-06-01T10:00:00"},
    ]
    result = _filter_by_span(records, "2024-03-01", None)
    assert len(result) == 1
    assert result[0]["timestamp"] == "2024-06-01T10:00:00"


def test_filter_until_excludes_newer():
    records = [
        {"timestamp": "2024-01-01T10:00:00"},
        {"timestamp": "2024-06-01T10:00:00"},
    ]
    result = _filter_by_span(records, None, "2024-03-01")
    assert len(result) == 1
    assert result[0]["timestamp"] == "2024-01-01T10:00:00"


def test_filter_both_bounds():
    records = [
        {"timestamp": "2023-12-01"},
        {"timestamp": "2024-02-01"},
        {"timestamp": "2024-08-01"},
    ]
    result = _filter_by_span(records, "2024-01-01", "2024-06-01")
    assert len(result) == 1
    assert result[0]["timestamp"] == "2024-02-01"


def test_filter_no_timestamp_always_kept():
    records = [{"author": "X"}, {"timestamp": "2024-06-01"}]
    result = _filter_by_span(records, "2025-01-01", None)
    # senza timestamp viene tenuto, con timestamp < since viene escluso
    assert any(r.get("author") == "X" for r in result)


def test_filter_empty_records():
    assert _filter_by_span([], "2024-01-01", "2024-12-31") == []


def test_filter_exact_boundary_included():
    records = [{"timestamp": "2024-06-01"}]
    result = _filter_by_span(records, "2024-06-01", "2024-06-01")
    assert len(result) == 1


# ── _channel_meta ─────────────────────────────────────────────────────────────


def test_channel_meta_name_extracted():
    data = {"channel": {"name": "rp-generale", "id": 123}, "messages": []}
    meta = _channel_meta(data)
    assert meta["channel"] == "rp-generale"


def test_channel_meta_count():
    data = {"channel": {}, "messages": [{"timestamp": "2024-01-01"}, {"timestamp": "2024-01-02"}]}
    meta = _channel_meta(data)
    assert meta["count"] == 2


def test_channel_meta_date_range():
    data = {
        "channel": {},
        "messages": [
            {"timestamp": "2024-03-01"},
            {"timestamp": "2024-01-01"},
            {"timestamp": "2024-06-01"},
        ],
    }
    meta = _channel_meta(data)
    assert meta["date_from"] == "2024-01-01"
    assert meta["date_to"] == "2024-06-01"


def test_channel_meta_empty_messages():
    data = {"channel": {"name": "vuoto"}, "messages": []}
    meta = _channel_meta(data)
    assert meta["count"] == 0
    assert meta["date_from"] is None
    assert meta["date_to"] is None


def test_channel_meta_missing_channel():
    data = {"messages": []}
    meta = _channel_meta(data)
    assert meta["channel"] == ""


def test_channel_meta_category():
    data = {
        "channel": {"name": "ch", "category": "IRP"},
        "messages": [],
    }
    assert _channel_meta(data)["parent_category"] == "IRP"


def test_channel_meta_channel_id():
    data = {"channel": {"id": 789, "name": "ch"}, "messages": []}
    assert _channel_meta(data)["channel_id"] == "789"


# ── _safe_resolve ─────────────────────────────────────────────────────────────


def test_safe_resolve_valid_json(tmp_path):
    f = tmp_path / "channel_abc.json"
    result = _safe_resolve(str(tmp_path), "channel_abc.json")
    assert result == f


def test_safe_resolve_path_traversal_rejected(tmp_path):
    result = _safe_resolve(str(tmp_path), "../outside.json")
    assert result is None


def test_safe_resolve_non_json_rejected(tmp_path):
    result = _safe_resolve(str(tmp_path), "channel.txt")
    assert result is None


def test_safe_resolve_absolute_path_rejected(tmp_path):
    result = _safe_resolve(str(tmp_path), "/etc/passwd.json")
    assert result is None


def test_safe_resolve_subdirectory_allowed(tmp_path):
    result = _safe_resolve(str(tmp_path), "subdir/file.json")
    assert result is not None
    assert result.suffix == ".json"
