"""Smoke tests for import_discord_roles.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from import_discord_roles import _parse_markdown_table, _row_to_record, import_roles  # noqa: E402

# Minimal sample markdown table (header + separator + 2 data rows)
SAMPLE_TABLE = """\
| name         |   position |                  id | mentionable   | administrator   | mention all   | manage guild   | manage roles   | manage channels   | kick members   | ban members   | webhooks   | tags   |
|--------------|------------|---------------------|---------------|-----------------|---------------|----------------|----------------|-------------------|----------------|---------------|------------|--------|
| GM           |         35 | 1320593702623772756 | Yes           | Yes             | No            | No             | No             | No                | No             | No            | No         |        |
| Tupperbox    |         34 | 1313637632357699627 | No            | No              | Yes           | No             | No             | No                | No             | No            | Yes        | Bot    |
"""


def test_parse_markdown_table_row_count():
    rows = _parse_markdown_table(SAMPLE_TABLE)
    assert len(rows) == 2


def test_parse_gm_row_schema():
    rows = _parse_markdown_table(SAMPLE_TABLE)
    gm = rows[0]
    record = _row_to_record(gm)

    # Schema keys
    assert set(record.keys()) == {"name", "id", "position", "mentionable", "is_bot", "permissions_flags"}

    # Values
    assert record["name"] == "GM"
    assert record["id"] == "1320593702623772756"
    assert record["position"] == 35
    assert record["mentionable"] is True
    assert record["is_bot"] is False
    assert "administrator" in record["permissions_flags"]
    # Non-permission columns not in flags
    assert "name" not in record["permissions_flags"]
    assert "tags" not in record["permissions_flags"]


def test_parse_bot_row():
    rows = _parse_markdown_table(SAMPLE_TABLE)
    tupperbox = rows[1]
    record = _row_to_record(tupperbox)

    assert record["is_bot"] is True
    assert record["mentionable"] is False
    assert "webhooks" in record["permissions_flags"]
    assert "mention all" in record["permissions_flags"]
    assert "administrator" not in record["permissions_flags"]


def test_import_roles_real_file(tmp_path):
    """Integration smoke test against the real export file."""
    real_input = Path(
        "/tmp/discord_import/roles/1312211590883442688_1778982271.279325_roles.txt"
    )
    if not real_input.exists():
        pytest.skip("Real input file not present")

    output = tmp_path / "roles.jsonl"
    count = import_roles(real_input, output)

    assert count >= 30, f"Expected >=30 roles, got {count}"

    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == count

    for line in lines:
        record = json.loads(line)
        assert isinstance(record["name"], str)
        assert isinstance(record["id"], str)
        assert isinstance(record["position"], int)
        assert isinstance(record["mentionable"], bool)
        assert isinstance(record["is_bot"], bool)
        assert isinstance(record["permissions_flags"], list)
