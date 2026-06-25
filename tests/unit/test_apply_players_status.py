"""Unit tests for scripts/apply_players_status.py — fuzzy matching + message annotation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from apply_players_status import load_players_mapping, main, print_stats, process_messages  # noqa: E402

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


# ── copertura righe mancanti (generato zai-glm, corretto Claude) ──────────────

def test_load_players_mapping_yaml_error(tmp_path, capsys):
    """Lines 28-30: YAML invalido → stderr + sys.exit(1)."""
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text(":\ninvalid: yaml: :", encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        load_players_mapping(bad_file)
    assert exc_info.value.code == 1
    assert "Failed to parse YAML" in capsys.readouterr().err


def test_load_players_mapping_players_not_list(tmp_path, capsys):
    """Lines 35-36: players non è una lista → sys.exit(1)."""
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("players: una_stringa", encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        load_players_mapping(bad_file)
    assert exc_info.value.code == 1
    assert 'Expected "players" to be a list' in capsys.readouterr().err


def test_load_players_mapping_skip_player_without_name(tmp_path):
    """Line 40: player senza 'name' → continue, non aggiunto al mapping."""
    file_path = tmp_path / "players.yaml"
    file_path.write_text("players:\n  - aliases: []\n  - name: Valid", encoding="utf-8")
    mapping = load_players_mapping(file_path)
    assert mapping == {"Valid": "Valid"}


def test_load_players_mapping_skip_non_list_aliases(tmp_path):
    """Line 44: aliases non-lista → continue, anche il nome viene skippato."""
    file_path = tmp_path / "players.yaml"
    file_path.write_text(
        "players:\n  - name: Player1\n    aliases: stringa\n  - name: Player2\n    aliases: [p2]",
        encoding="utf-8",
    )
    mapping = load_players_mapping(file_path)
    # Player1 skippato perché aliases non è lista; Player2 ok
    assert "Player1" not in mapping
    assert mapping == {"Player2": "Player2", "p2": "Player2"}


def test_process_messages_no_author_fields(tmp_path):
    """Line 89: messaggio senza author_nick e author_name → player_status='unknown'."""
    input_file = tmp_path / "messages.jsonl"
    output_file = tmp_path / "output.jsonl"
    input_file.write_text(json.dumps({"text": "hello, no author"}), encoding="utf-8")
    mapping = {"Player1": "Player1"}
    stats = process_messages(input_file, output_file, mapping, 0.5, False)
    assert stats["unknown"] == 1
    record = json.loads(output_file.read_text())
    assert record["player_status"] == "unknown"


def test_process_messages_file_not_found(tmp_path):
    """Lines 130-132: file messaggi non trovato → sys.exit(1)."""
    output_file = tmp_path / "out.jsonl"
    with pytest.raises(SystemExit) as exc_info:
        process_messages(tmp_path / "nonexistent.jsonl", output_file, {}, 0.5, False)
    assert exc_info.value.code == 1


def test_print_stats_output(capsys):
    """Lines 159-174: print_stats stampa tutte le sezioni."""
    stats = {
        "total": 10,
        "active": 8,
        "unknown": 2,
        "player_counts": {"Alice": 5, "Bob": 3},
    }
    print_stats(stats)
    out = capsys.readouterr().out
    assert "Total messages: 10" in out
    assert "Active matches: 8" in out
    assert "Unknown: 2" in out
    assert "80.00%" in out
    assert "Alice: 5" in out


def test_print_stats_empty(capsys):
    """Lines 159-174: print_stats con total=0 → match rate 0%."""
    stats = {"total": 0, "active": 0, "unknown": 0, "player_counts": {}}
    print_stats(stats)
    out = capsys.readouterr().out
    assert "0.00%" in out


def test_main_invalid_threshold(monkeypatch, capsys):
    """Lines 220-222: threshold fuori [0,1] → sys.exit(1)."""
    monkeypatch.setattr("sys.argv", ["script", "--threshold", "1.5"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert "threshold" in capsys.readouterr().err.lower()


def test_main_players_yaml_not_found(monkeypatch, tmp_path, capsys):
    """Lines 225-229: --players-yaml non esiste → sys.exit(1)."""
    msg_file = tmp_path / "messages.jsonl"
    msg_file.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("sys.argv", [
        "script",
        "--players-yaml", str(tmp_path / "missing.yaml"),
        "--messages", str(msg_file),
    ])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


def test_main_messages_file_not_found(monkeypatch, tmp_path, capsys):
    """Lines 230-234: --messages non esiste → sys.exit(1)."""
    yaml_file = tmp_path / "players.yaml"
    yaml_file.write_text("players: []", encoding="utf-8")
    monkeypatch.setattr("sys.argv", [
        "script",
        "--players-yaml", str(yaml_file),
        "--messages", str(tmp_path / "missing.jsonl"),
    ])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


def test_main_dry_run_success(monkeypatch, tmp_path, capsys):
    """Lines 179-252: main() full path con --dry-run."""
    yaml_file = tmp_path / "players.yaml"
    yaml_file.write_text("players:\n  - name: P1\n    aliases: [p1]", encoding="utf-8")
    msg_file = tmp_path / "messages.jsonl"
    msg_file.write_text('{"author_name": "P1", "text": "hi"}', encoding="utf-8")
    out_file = tmp_path / "out.jsonl"
    monkeypatch.setattr("sys.argv", [
        "script",
        "--players-yaml", str(yaml_file),
        "--messages", str(msg_file),
        "--output", str(out_file),
        "--dry-run",
    ])
    main()
    out = capsys.readouterr().out
    assert "Total messages" in out


def test_process_messages_skips_blank_lines(tmp_path):
    """Line 89: righe vuote nel JSONL → continue."""
    input_file = tmp_path / "messages.jsonl"
    output_file = tmp_path / "output.jsonl"
    mapping = {"Player1": "Player1"}
    input_file.write_text('\n\n{"author_name": "Player1"}\n\n', encoding="utf-8")
    stats = process_messages(input_file, output_file, mapping, 0.5, False)
    assert stats["total"] == 1


def test_process_messages_invalid_json_line_skipped(tmp_path, capsys):
    """Lines 92-94: JSON invalido → Warning su stderr, riga skippata."""
    input_file = tmp_path / "messages.jsonl"
    output_file = tmp_path / "output.jsonl"
    input_file.write_text('not_json\n{"author_name": "P1"}\n', encoding="utf-8")
    mapping = {"P1": "P1"}
    stats = process_messages(input_file, output_file, mapping, 0.5, False)
    assert stats["total"] == 1
    assert "Warning" in capsys.readouterr().err


def test_process_messages_permission_error_exits(tmp_path, capsys):
    """Lines 133-135: PermissionError → stderr + sys.exit(1)."""
    from unittest.mock import patch
    input_file = tmp_path / "messages.jsonl"
    output_file = tmp_path / "output.jsonl"
    input_file.write_text('{"author_name": "P1"}\n', encoding="utf-8")
    with patch("pathlib.Path.open", side_effect=PermissionError("access denied")):
        with pytest.raises(SystemExit) as exc:
            process_messages(input_file, output_file, {"P1": "P1"}, 0.5, False)
    assert exc.value.code == 1
    assert "Permission denied" in capsys.readouterr().err


def test_process_messages_generic_exception_exits(tmp_path, capsys):
    """Lines 136-138: Exception generica → stderr + sys.exit(1)."""
    from unittest.mock import patch
    input_file = tmp_path / "messages.jsonl"
    output_file = tmp_path / "output.jsonl"
    input_file.write_text('{"author_name": "P1"}\n', encoding="utf-8")
    with patch("scripts.apply_players_status.rapidfuzz.process.extractOne",
               side_effect=RuntimeError("crash")):
        with pytest.raises(SystemExit) as exc:
            process_messages(input_file, output_file, {"P1": "P1"}, 0.5, False)
    assert exc.value.code == 1
    assert "Unexpected error" in capsys.readouterr().err


def test_process_messages_atomic_move_failure_exits(tmp_path, capsys):
    """Lines 148-152: shutil.move fallisce → cleanup + sys.exit(1)."""
    from unittest.mock import patch
    input_file = tmp_path / "messages.jsonl"
    output_file = tmp_path / "output.jsonl"
    input_file.write_text('{"author_name": "P1"}\n', encoding="utf-8")
    with patch("scripts.apply_players_status.shutil.move",
               side_effect=OSError("disk full")):
        with pytest.raises(SystemExit) as exc:
            process_messages(input_file, output_file, {"P1": "P1"}, 0.5, False)
    assert exc.value.code == 1
    assert "Failed to move" in capsys.readouterr().err
