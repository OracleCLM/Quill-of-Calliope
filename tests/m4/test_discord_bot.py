"""Discord bot unit tests — mock discord.py, no real connection."""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))

# Set token before import to avoid sys.exit at module level
os.environ.setdefault("CALLIOPE_DISCORD_BOT_TOKEN", "test_token_placeholder")

from discord_bot import get_state_path, load_guild_state  # noqa: E402
from narrative_state import NarrativeState  # noqa: E402


def _make_state_json(location: str = "Yokai Capital") -> dict:
    """Minimal NarrativeState-compatible JSON (matches NarrativeState dataclass fields)."""
    return {
        "chars": {},
        "plot_threads": [],
        "current_location": location,
        "current_time": "unknown",
        "scene_count": 0,
    }


def test_state_path_per_guild():
    p1 = get_state_path("guild_1")
    p2 = get_state_path("guild_2")
    assert p1 != p2
    assert "guild_1" in str(p1)
    assert "guild_2" in str(p2)


def test_state_path_structure():
    path = get_state_path("12345")
    assert path.name == "12345.json"
    assert "discord_state" in str(path)


def test_load_guild_state_missing_returns_none():
    result = load_guild_state("nonexistent_guild_xyz_99999")
    assert result is None


def test_load_guild_state_existing(tmp_path):
    state_file = tmp_path / "guild_123.json"
    state_file.write_text(json.dumps(_make_state_json("Test Location")), encoding="utf-8")
    with patch("discord_bot.get_state_path", return_value=state_file):
        result = load_guild_state("guild_123")
    assert isinstance(result, NarrativeState)
    assert result.current_location == "Test Location"


def test_per_guild_isolation(tmp_path):
    file_a = tmp_path / "guild_A.json"
    file_b = tmp_path / "guild_B.json"
    file_a.write_text(json.dumps(_make_state_json("Abyss Castle")), encoding="utf-8")
    file_b.write_text(json.dumps(_make_state_json("Slums")), encoding="utf-8")

    def _mock_path(gid):
        return tmp_path / f"guild_{gid}.json"

    with patch("discord_bot.get_state_path", side_effect=_mock_path):
        state_a = load_guild_state("A")
        state_b = load_guild_state("B")
    assert state_a.current_location != state_b.current_location
    assert state_a.current_location == "Abyss Castle"
    assert state_b.current_location == "Slums"


def test_bot_token_env_var_name():
    import discord_bot
    assert discord_bot._ENV_TOKEN == "CALLIOPE_DISCORD_BOT_TOKEN"


def test_valid_states_set():
    import discord_bot
    assert hasattr(discord_bot, "_VALID_STATES")
    assert "idle" in discord_bot._VALID_STATES
    assert "talking" in discord_bot._VALID_STATES
