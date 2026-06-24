"""Unit test per scripts/import_discord_roles.py (base zai-glm, verificato Claude)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from scripts.import_discord_roles import (
    _parse_bool,
    _parse_markdown_table,
    _row_to_record,
    _setup_logging,
    import_roles,
    main,
)


# ── _parse_bool ───────────────────────────────────────────────────────────────

def test_parse_bool_true_variations():
    assert _parse_bool("yes") is True
    assert _parse_bool("Yes") is True
    assert _parse_bool("YES") is True
    assert _parse_bool("  yes  ") is True


def test_parse_bool_false_variations():
    assert _parse_bool("no") is False
    assert _parse_bool("No") is False
    assert _parse_bool("") is False
    assert _parse_bool("  ") is False


def test_parse_bool_only_yes_is_true():
    assert _parse_bool("true") is False
    assert _parse_bool("1") is False
    assert _parse_bool("y") is False


# ── _parse_markdown_table ──────────────────────────────────────────────────────

def test_parse_markdown_table_valid():
    text = "| name | id |\n|---|---|\n| Admin | 1 |\n| Mod | 2 |"
    result = _parse_markdown_table(text)
    assert result == [{"name": "Admin", "id": "1"}, {"name": "Mod", "id": "2"}]


def test_parse_markdown_table_no_header_raises():
    with pytest.raises(ValueError, match="No markdown table header found"):
        _parse_markdown_table("just some text")


def test_parse_markdown_table_empty_rows():
    text = "| name | id |\n|---|---|"
    assert _parse_markdown_table(text) == []


def test_parse_markdown_table_skips_malformed_rows():
    text = "| name | id | color |\n|---|---|---|\n| A | 1 | red |\n| B | blue |"
    result = _parse_markdown_table(text)
    assert result == [{"name": "A", "id": "1", "color": "red"}]


def test_parse_markdown_table_whitespace_stripped():
    text = "|  name  |  id  |\n|---|---|\n|  Test  |  99  |"
    result = _parse_markdown_table(text)
    assert result == [{"name": "Test", "id": "99"}]


def test_parse_markdown_table_extra_empty_lines():
    text = "\n| name | id |\n|---|---|\n\n| A | 1 |\n\n"
    result = _parse_markdown_table(text)
    assert result == [{"name": "A", "id": "1"}]


# ── _row_to_record ─────────────────────────────────────────────────────────────

def test_row_to_record_basic():
    row = {"name": "Member", "id": "123", "position": "5", "tags": ""}
    result = _row_to_record(row)
    assert result["name"] == "Member"
    assert result["id"] == "123"
    assert result["position"] == 5
    assert result["mentionable"] is False
    assert result["is_bot"] is False
    assert result["permissions_flags"] == []


def test_row_to_record_with_permissions():
    row = {
        "name": "Admin", "id": "1", "position": "0", "tags": "",
        "administrator": "yes", "ban members": "Yes", "kick members": "no",
    }
    result = _row_to_record(row)
    assert "administrator" in result["permissions_flags"]
    assert "ban members" in result["permissions_flags"]
    assert "kick members" not in result["permissions_flags"]


def test_row_to_record_bot_tag_detected():
    row = {"name": "MusicBot", "id": "999", "position": "10", "tags": "bot, music"}
    assert _row_to_record(row)["is_bot"] is True


def test_row_to_record_mentionable():
    row = {"name": "Announcements", "id": "555", "position": "2", "tags": "", "mentionable": "YES"}
    assert _row_to_record(row)["mentionable"] is True


# ── _setup_logging ─────────────────────────────────────────────────────────────

def test_setup_logging_runs():
    """Lines 30-33: _setup_logging non crasha, chiama reconfigure su stdout (verbose=True/False)."""
    mock_stream = MagicMock()
    with patch("sys.stdout", mock_stream):
        _setup_logging(verbose=False)
        _setup_logging(verbose=True)
    assert mock_stream.reconfigure.call_count == 2


# ── _parse_markdown_table: line 60 (continue) ─────────────────────────────────

def test_parse_markdown_table_non_pipe_body_line_skipped():
    """Line 60: riga senza '|' nel corpo → continue (skip silenzioso)."""
    text = "| name | id |\n|---|---|\nnon pipe line\n| A | 1 |"
    result = _parse_markdown_table(text)
    assert result == [{"name": "A", "id": "1"}]


# ── import_roles ───────────────────────────────────────────────────────────────

def _make_roles_table(n: int = 1) -> str:
    header = "| name | id | position | tags |\n|---|---|---|---|\n"
    rows = "".join(f"| Role{i} | {i} | {i} | |\n" for i in range(n))
    return header + rows


def test_import_roles_writes_jsonl(tmp_path):
    """Lines 101-115: import_roles scrive JSONL e ritorna count."""
    input_file = tmp_path / "roles.txt"
    input_file.write_text(_make_roles_table(3), encoding="utf-8")
    output_file = tmp_path / "out.jsonl"
    count = import_roles(input_file, output_file)
    assert count == 3
    lines = output_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    record = json.loads(lines[0])
    assert record["name"] == "Role0"


def test_import_roles_creates_parent_dir(tmp_path):
    """Line 105: parent dir creata se non esiste."""
    input_file = tmp_path / "roles.txt"
    input_file.write_text(_make_roles_table(1), encoding="utf-8")
    output_file = tmp_path / "subdir" / "nested" / "out.jsonl"
    count = import_roles(input_file, output_file)
    assert count == 1
    assert output_file.exists()


# ── main() ────────────────────────────────────────────────────────────────────

def test_main_exits_1_when_count_below_threshold(tmp_path, monkeypatch):
    """Line 144-146: count < 30 → sys.exit(1)."""
    input_file = tmp_path / "roles.txt"
    input_file.write_text(_make_roles_table(1), encoding="utf-8")
    output_file = tmp_path / "out.jsonl"
    monkeypatch.setattr("sys.argv", [
        "import_discord_roles.py",
        "--input", str(input_file),
        "--output", str(output_file),
    ])
    with patch("scripts.import_discord_roles._setup_logging"):
        with pytest.raises(SystemExit) as exc:
            main()
    assert exc.value.code == 1


def test_main_success(tmp_path, monkeypatch):
    """Lines 119-148: main() con ≥30 ruoli → successo, nessuna exit."""
    input_file = tmp_path / "roles.txt"
    input_file.write_text(_make_roles_table(30), encoding="utf-8")
    output_file = tmp_path / "out.jsonl"
    monkeypatch.setattr("sys.argv", [
        "import_discord_roles.py",
        "--input", str(input_file),
        "--output", str(output_file),
    ])
    with patch("scripts.import_discord_roles._setup_logging"):
        main()
    lines = output_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 30
