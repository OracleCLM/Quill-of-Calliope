"""Tests for scripts/merge_delta_messages.py — dedup + sort logic."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
import merge_delta_messages  # noqa: E402


def _dce_msg(mid: str, ts: str, content: str = "hello") -> dict:
    return {
        "ID": mid,
        "Timestamp": ts,
        "Author": {"ID": "999", "Name": "testuser", "Nickname": None},
        "Content": content,
        "Attachments": [],
    }


def _write_jsonl(path: Path, records: list) -> None:
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


def _write_dce_json(path: Path, msgs: list) -> None:
    path.write_text(json.dumps(msgs), encoding="utf-8")


class TestMergeDeltaMessages:
    def test_baseline_80dup_20new(self, tmp_path):
        # 100 existing messages (IDs 1000..1099)
        existing = [
            {"message_id": str(1000 + i), "timestamp": f"2023-01-01T{i:02d}:00:00Z"}
            for i in range(100)
        ]
        out = tmp_path / "messages_clean.jsonl"
        _write_jsonl(out, existing)

        # Delta: 80 duplicates (1000..1079) + 20 new (2000..2019)
        delta_dir = tmp_path / "delta_ts"
        delta_dir.mkdir()
        delta_msgs = [_dce_msg(str(1000 + i), f"2023-01-02T{i:02d}:00:00Z") for i in range(80)]
        delta_msgs += [_dce_msg(str(2000 + i), f"2023-01-03T{i:02d}:00:00Z") for i in range(20)]
        _write_dce_json(delta_dir / "delta.json", delta_msgs)

        with patch("sys.argv", ["script", "--delta-dir", str(delta_dir), "--main-output", str(out)]):
            merge_delta_messages.main()

        lines = [json.loads(ln) for ln in out.read_text().splitlines() if ln.strip()]
        assert len(lines) == 120
        ids = {m["message_id"] for m in lines}
        assert len(ids) == 120  # zero duplicates
        assert "2000" in ids
        assert "1099" in ids
        timestamps = [m["timestamp"] for m in lines]
        assert timestamps == sorted(timestamps)

    def test_no_existing_file(self, tmp_path):
        out = tmp_path / "messages_clean.jsonl"
        delta_dir = tmp_path / "delta"
        delta_dir.mkdir()

        base = datetime(2023, 6, 1)
        msgs = [_dce_msg(str(i), (base + timedelta(hours=i)).isoformat()) for i in range(50)]
        _write_dce_json(delta_dir / "data.json", msgs)

        with patch("sys.argv", ["script", "--delta-dir", str(delta_dir), "--main-output", str(out)]):
            merge_delta_messages.main()

        lines = [json.loads(ln) for ln in out.read_text().splitlines() if ln.strip()]
        assert len(lines) == 50
        timestamps = [m["timestamp"] for m in lines]
        assert timestamps == sorted(timestamps)

    def test_empty_delta_dir(self, tmp_path):
        # Pre-existing file with 10 messages
        out = tmp_path / "messages_clean.jsonl"
        existing = [
            {"message_id": str(i), "timestamp": f"2023-01-01T{i:02d}:00:00Z"}
            for i in range(10)
        ]
        _write_jsonl(out, existing)

        delta_dir = tmp_path / "delta_empty"
        delta_dir.mkdir()

        with patch("sys.argv", ["script", "--delta-dir", str(delta_dir), "--main-output", str(out)]):
            with pytest.raises(SystemExit) as exc:
                merge_delta_messages.main()
        assert exc.value.code == 0

        # File unchanged
        lines = [ln for ln in out.read_text().splitlines() if ln.strip()]
        assert len(lines) == 10
