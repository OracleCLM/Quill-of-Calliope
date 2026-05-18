"""Unit tests for scripts/parse_character_list_thread.py — synthetic DCE files."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from parse_character_list_thread import parse_threads  # noqa: E402

CHANNEL_ID = "1320529977732632697"


def _dce_thread(name: str, thread_id: str, category_id: str = CHANNEL_ID,
                msgs: list[dict] | None = None) -> dict:
    msgs = msgs or [
        {"id": "msg1", "type": "Default", "timestamp": "2024-12-01T10:00:00+00:00",
         "timestampEdited": None, "content": f"Name: {name}\nRace: Human",
         "author": {"id": "user_001", "name": "testuser"}}
    ]
    return {
        "guild": {"id": "guild1", "name": "Test Guild"},
        "channel": {"id": thread_id, "type": "GuildPublicThread",
                     "categoryId": category_id, "category": "characters-list",
                     "name": name, "topic": None},
        "messages": msgs,
        "messageCount": len(msgs),
    }


def _write_thread(tmp_path: Path, filename: str, data: dict) -> Path:
    p = tmp_path / filename
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


class TestParseThreadsBasic:
    def test_single_thread_written(self, tmp_path):
        _write_thread(tmp_path, "thread1.json", _dce_thread("Rusty", "thread_001"))
        out = tmp_path / "out.jsonl"
        parse_threads(str(tmp_path), CHANNEL_ID, str(out))
        lines = [json.loads(ln) for ln in out.read_text().splitlines() if ln.strip()]
        assert len(lines) == 1
        assert lines[0]["char_name"] == "Rusty"
        assert lines[0]["thread_id"] == "thread_001"

    def test_multiple_threads(self, tmp_path):
        for name, tid in [("Rusty", "t1"), ("Aurora", "t2"), ("Grimm", "t3")]:
            _write_thread(tmp_path, f"{tid}.json", _dce_thread(name, tid))
        out = tmp_path / "out.jsonl"
        parse_threads(str(tmp_path), CHANNEL_ID, str(out))
        lines = out.read_text().splitlines()
        assert len(lines) == 3

    def test_output_schema_fields(self, tmp_path):
        _write_thread(tmp_path, "t.json", _dce_thread("TestChar", "tid_01"))
        out = tmp_path / "out.jsonl"
        parse_threads(str(tmp_path), CHANNEL_ID, str(out))
        record = json.loads(out.read_text().splitlines()[0])
        for field in ("char_name", "thread_id", "thread_name", "author_id",
                      "author_username", "sheet_text", "created_at",
                      "last_updated", "msg_count_in_thread"):
            assert field in record, f"Missing field: {field}"


class TestFiltering:
    def test_non_thread_type_skipped(self, tmp_path):
        data = _dce_thread("SomeChar", "t1")
        data["channel"]["type"] = "GuildTextChat"
        _write_thread(tmp_path, "main.json", data)
        out = tmp_path / "out.jsonl"
        parse_threads(str(tmp_path), CHANNEL_ID, str(out))
        assert out.read_text().strip() == ""

    def test_wrong_category_id_skipped(self, tmp_path):
        _write_thread(tmp_path, "t.json", _dce_thread("Char", "t1", category_id="9999"))
        out = tmp_path / "out.jsonl"
        parse_threads(str(tmp_path), CHANNEL_ID, str(out))
        assert out.read_text().strip() == ""

    def test_ooc_skip_keyword(self, tmp_path):
        _write_thread(tmp_path, "t.json", _dce_thread("ooc chat", "t1"))
        out = tmp_path / "out.jsonl"
        parse_threads(str(tmp_path), CHANNEL_ID, str(out))
        assert out.read_text().strip() == ""

    def test_poll_false_positive_fixed(self, tmp_path):
        # 'poll' is a word-boundary match — 'Apollyon' should NOT be skipped
        _write_thread(tmp_path, "t.json", _dce_thread("Apollyon", "t2"))
        out = tmp_path / "out.jsonl"
        parse_threads(str(tmp_path), CHANNEL_ID, str(out))
        lines = [ln for ln in out.read_text().splitlines() if ln.strip()]
        assert len(lines) == 1
        assert json.loads(lines[0])["char_name"] == "Apollyon"

    def test_min_msgs_filter(self, tmp_path):
        data = _dce_thread("FewMsgs", "t1", msgs=[
            {"id": "m1", "type": "Default", "timestamp": "2024-01-01T00:00:00+00:00",
             "timestampEdited": None, "content": "hi",
             "author": {"id": "u1", "name": "user"}}
        ])
        data["messageCount"] = 1
        _write_thread(tmp_path, "t.json", data)
        out = tmp_path / "out.jsonl"
        parse_threads(str(tmp_path), CHANNEL_ID, str(out), min_msgs=2)
        assert out.read_text().strip() == ""


class TestEdgeCases:
    def test_empty_directory(self, tmp_path):
        out = tmp_path / "out.jsonl"
        parse_threads(str(tmp_path), CHANNEL_ID, str(out))  # no crash

    def test_malformed_json_skipped(self, tmp_path):
        (tmp_path / "bad.json").write_text("{bad json{{", encoding="utf-8")
        _write_thread(tmp_path, "good.json", _dce_thread("GoodChar", "t1"))
        out = tmp_path / "out.jsonl"
        parse_threads(str(tmp_path), CHANNEL_ID, str(out))
        lines = [ln for ln in out.read_text().splitlines() if ln.strip()]
        assert len(lines) == 1

    def test_sheet_text_concatenated(self, tmp_path):
        msgs = [
            {"id": "m1", "type": "Default", "timestamp": "2024-01-01T10:00:00+00:00",
             "timestampEdited": None, "content": "Part one of the sheet.",
             "author": {"id": "u1", "name": "user"}},
            {"id": "m2", "type": "Default", "timestamp": "2024-01-01T10:01:00+00:00",
             "timestampEdited": None, "content": "Part two of the sheet.",
             "author": {"id": "u1", "name": "user"}},
        ]
        _write_thread(tmp_path, "t.json", _dce_thread("Multi", "t1", msgs=msgs))
        out = tmp_path / "out.jsonl"
        parse_threads(str(tmp_path), CHANNEL_ID, str(out))
        record = json.loads(out.read_text().splitlines()[0])
        assert "Part one" in record["sheet_text"]
        assert "Part two" in record["sheet_text"]

    def test_last_updated_uses_max_timestamp(self, tmp_path):
        msgs = [
            {"id": "m1", "type": "Default", "timestamp": "2024-01-01T10:00:00+00:00",
             "timestampEdited": "2024-06-01T12:00:00+00:00", "content": "edited msg",
             "author": {"id": "u1", "name": "user"}},
            {"id": "m2", "type": "Default", "timestamp": "2024-03-01T09:00:00+00:00",
             "timestampEdited": None, "content": "later msg",
             "author": {"id": "u1", "name": "user"}},
        ]
        _write_thread(tmp_path, "t.json", _dce_thread("TimeChar", "t1", msgs=msgs))
        out = tmp_path / "out.jsonl"
        parse_threads(str(tmp_path), CHANNEL_ID, str(out))
        record = json.loads(out.read_text().splitlines()[0])
        # max ts is the edited timestamp 2024-06-01
        assert "2024-06-01" in record["last_updated"]
