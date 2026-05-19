"""TDB1-TDB3: Discord bot smoke tests — startup, heartbeat, auto-channels."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch


_REPO = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_REPO / "scripts"))
sys.path.insert(0, str(_REPO))


# ── TDB1: bot startup fails gracefully without token ─────────────────────────

def test_tdb1_bot_startup_missing_token(tmp_path):
    """Bot exits 1 with clear error when CALLIOPE_DISCORD_BOT_TOKEN not set."""
    env = dict(os.environ)
    env.pop("CALLIOPE_DISCORD_BOT_TOKEN", None)

    result = subprocess.run(
        [sys.executable, str(_REPO / "scripts" / "discord_bot.py")],
        cwd=str(_REPO),
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 1
    combined = result.stdout + result.stderr
    assert "CALLIOPE_DISCORD_BOT_TOKEN" in combined or "Missing" in combined


# ── TDB2: heartbeat script valid bash syntax ──────────────────────────────────

def test_tdb2_heartbeat_script_syntax():
    """discord_bot_heartbeat.sh passes bash -n syntax check."""
    script = _REPO / "scripts" / "discord_bot_heartbeat.sh"
    assert script.exists(), f"Heartbeat script not found: {script}"
    result = subprocess.run(
        ["bash", "-n", str(script)],
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 0, f"bash -n failed: {result.stderr}"


# ── TDB3: auto-channels env parse ───────────────────────────────────────────

def test_tdb3_auto_channels_env_parse():
    """CALLIOPE_AUTO_CHANNELS env var is parsed to set of ints correctly."""
    # Test with patched env (re-import the module to trigger parse)
    import importlib

    with patch.dict(os.environ, {"CALLIOPE_AUTO_CHANNELS": "111222,333444,555666"}):
        import discord_bot
        importlib.reload(discord_bot)
        # After reload, check _AUTO_CHANNELS
        assert 111222 in discord_bot._AUTO_CHANNELS
        assert 333444 in discord_bot._AUTO_CHANNELS
        assert 555666 in discord_bot._AUTO_CHANNELS

    # Reload without env to restore clean state
    os.environ.pop("CALLIOPE_AUTO_CHANNELS", None)
    importlib.reload(discord_bot)
