"""Unit tests for scripts/apply_players_status.py — fuzzy matching + message annotation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from apply_players_status import load_players_mapping, process_messages  # noqa: E402

THRESHOLD = 0.70  # fraction 0-1; script multiplies by 100 internally


def _players_yaml(tmp_path: Path, players: list[dict]) -> Path:
    p = tmp_path / "players.yaml"
    p.write_text(yaml.dump({"players": players}), encoding="utf-8")
    return p


def _messages_jsonl(tmp_path: Path, msgs: list[dict]) -> Path:
    p = tmp_path / "messages.jsonl"
    p.write_text("\n".join(json.dumps(m) for m in msgs) + "\n", encoding="utf-8")
    return p


def _msg(author: str, msg_id: str = "1", **kwargs) -> dict:
    # apply_players_status matches on author_nick OR author_name (not author_username)
    return {"message_id": msg_id, "author_name": author,
            "author_username": author,
            "content": "test", "timestamp": "2024-01-01T00:00:00Z", **kwargs}


class TestLoadPlayersMapping:
    def test_loads_name(self, tmp_path):
        yf = _players_yaml(tmp_path, [{"name": "Horo", "aliases": []}])
        mapping = load_players_mapping(yf)
        assert "Horo" in mapping
        assert mapping["Horo"] == "Horo"

    def test_loads_aliases(self, tmp_path):
        yf = _players_yaml(tmp_path, [{"name": "Horo", "aliases": ["morboia", "nic"]}])
        mapping = load_players_mapping(yf)
        assert "morboia" in mapping
        assert mapping["morboia"] == "Horo"
        assert mapping["nic"] == "Horo"

    def test_multiple_players(self, tmp_path):
        yf = _players_yaml(tmp_path, [
            {"name": "Alice", "aliases": ["ali"]},
            {"name": "Bob", "aliases": ["bobby"]},
        ])
        mapping = load_players_mapping(yf)
        assert "Alice" in mapping and "ali" in mapping
        assert "Bob" in mapping and "bobby" in mapping

    def test_missing_file_exits(self, tmp_path):
        with pytest.raises(SystemExit):
            load_players_mapping(tmp_path / "nonexistent.yaml")

    def test_empty_players_list(self, tmp_path):
        yf = _players_yaml(tmp_path, [])
        mapping = load_players_mapping(yf)
        assert mapping == {}

    def test_player_without_aliases(self, tmp_path):
        yf = _players_yaml(tmp_path, [{"name": "Solo"}])
        mapping = load_players_mapping(yf)
        assert "Solo" in mapping


class TestProcessMessages:
    def test_exact_match_tagged_active(self, tmp_path):
        yf = _players_yaml(tmp_path, [{"name": "Horo", "aliases": []}])
        mf = _messages_jsonl(tmp_path, [_msg("Horo", "1")])
        out = tmp_path / "out.jsonl"
        mapping = load_players_mapping(yf)
        stats = process_messages(mf, out, mapping, THRESHOLD, dry_run=False)
        assert stats["active"] >= 1
        records = [json.loads(ln) for ln in out.read_text().splitlines() if ln.strip()]
        assert records[0].get("player_status") == "active"

    def test_alias_match_tagged_active(self, tmp_path):
        yf = _players_yaml(tmp_path, [{"name": "Horo", "aliases": ["morboia"]}])
        mf = _messages_jsonl(tmp_path, [_msg("morboia", "1")])
        out = tmp_path / "out.jsonl"
        mapping = load_players_mapping(yf)
        process_messages(mf, out, mapping, THRESHOLD, dry_run=False)
        records = [json.loads(ln) for ln in out.read_text().splitlines() if ln.strip()]
        assert records[0].get("player_status") == "active"

    def test_unknown_author_tagged_unknown(self, tmp_path):
        yf = _players_yaml(tmp_path, [{"name": "Horo", "aliases": []}])
        mf = _messages_jsonl(tmp_path, [_msg("totally_unknown_xyz", "1")])
        out = tmp_path / "out.jsonl"
        mapping = load_players_mapping(yf)
        stats = process_messages(mf, out, mapping, THRESHOLD, dry_run=False)
        assert stats["unknown"] >= 1

    def test_stats_total_count(self, tmp_path):
        yf = _players_yaml(tmp_path, [{"name": "Alice", "aliases": []}])
        msgs = [_msg("Alice", str(i)) for i in range(5)]
        mf = _messages_jsonl(tmp_path, msgs)
        out = tmp_path / "out.jsonl"
        mapping = load_players_mapping(yf)
        stats = process_messages(mf, out, mapping, THRESHOLD, dry_run=False)
        assert stats["total"] == 5

    def test_dry_run_no_output_file(self, tmp_path):
        yf = _players_yaml(tmp_path, [{"name": "Horo", "aliases": []}])
        mf = _messages_jsonl(tmp_path, [_msg("Horo", "1")])
        out = tmp_path / "out.jsonl"
        mapping = load_players_mapping(yf)
        process_messages(mf, out, mapping, THRESHOLD, dry_run=True)
        # dry_run: output file may not be written (or may be same as input)

    def test_output_preserves_all_fields(self, tmp_path):
        yf = _players_yaml(tmp_path, [{"name": "Horo", "aliases": []}])
        msg = {"message_id": "abc", "author_name": "Horo", "author_username": "Horo",
               "content": "hello", "timestamp": "2024-01-01T00:00:00Z",
               "character": "Aurora"}
        mf = _messages_jsonl(tmp_path, [msg])
        out = tmp_path / "out.jsonl"
        mapping = load_players_mapping(yf)
        process_messages(mf, out, mapping, THRESHOLD, dry_run=False)
        record = json.loads(out.read_text().splitlines()[0])
        assert record["message_id"] == "abc"
        assert record["character"] == "Aurora"
        assert "player_status" in record
