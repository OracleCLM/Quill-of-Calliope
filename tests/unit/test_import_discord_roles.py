"""Unit test per scripts/import_discord_roles.py (base zai-glm, verificato Claude)."""
from __future__ import annotations

import pytest

from scripts.import_discord_roles import (
    _parse_bool,
    _parse_markdown_table,
    _row_to_record,
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
