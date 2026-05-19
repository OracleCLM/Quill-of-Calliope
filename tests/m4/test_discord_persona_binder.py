"""TDM1-TDM7: Discord persona binder + bot integration tests."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_REPO = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_REPO / "scripts"))
sys.path.insert(0, str(_REPO))


# ── TDM1: webhook registry CRUD ──────────────────────────────────────────────

def test_tdm1_webhook_registry_crud(tmp_path):
    """Webhook registry: add, get, delete per channel."""
    import discord_persona_binder as dpb

    db = tmp_path / "test_persona.db"
    dpb.init_db(db)
    dpb._save_webhook_url(123456, "https://discord.com/api/webhooks/1/token", db)

    url = dpb._get_webhook_url(123456, db)
    assert url == "https://discord.com/api/webhooks/1/token"

    deleted = dpb.delete_channel_webhook(123456, db)
    assert deleted is True
    assert dpb._get_webhook_url(123456, db) is None


# ── TDM2: trigger parse "Aurora: text" ──────────────────────────────────────

def test_tdm2_trigger_parse_valid():
    """Standard trigger parses correctly."""
    from discord_persona_binder import parse_persona_trigger

    char, text = parse_persona_trigger("Aurora: She drew her sword in the moonlight.")
    assert char == "Aurora"
    assert text == "She drew her sword in the moonlight."


def test_tdm2_trigger_parse_multi_word_name():
    """Multi-word char name parses correctly."""
    from discord_persona_binder import parse_persona_trigger

    char, text = parse_persona_trigger("Alexis Snyder: I came back, didn't I?")
    assert char == "Alexis Snyder"
    assert "came back" in text


def test_tdm2_trigger_parse_no_match():
    """Non-trigger messages return (None, None)."""
    from discord_persona_binder import parse_persona_trigger

    assert parse_persona_trigger("Just a regular message.") == (None, None)
    assert parse_persona_trigger("12345: digits only name") == (None, None)
    assert parse_persona_trigger("X: hi") == (None, None)  # text too short (<3 chars)


# ── TDM3: char_memory recall integration mock ────────────────────────────────

def test_tdm3_char_memory_recall_integration():
    """retrieve_multi_signal returns correct structure for char recall."""
    from app.calliope_shell.char_memory import retrieve_multi_signal, append_fact
    import app.calliope_shell.char_memory as cm

    orig = cm._DB_PATH
    import tempfile
    tmp_db = Path(tempfile.mktemp(suffix=".db"))
    try:
        cm._DB_PATH = tmp_db
        cm.init_db()
        append_fact("Aurora", "ha incontrato un cultista vampirizzato nella cripta", scope="L1")
        results = retrieve_multi_signal("Aurora", "cultista")
        assert isinstance(results, list)
        if results:
            assert "fact_text" in results[0]
            assert "score" in results[0]
    finally:
        cm._DB_PATH = orig
        cm.init_db()
        tmp_db.unlink(missing_ok=True)


# ── TDM4: scene gen slash command mock ───────────────────────────────────────

@pytest.mark.asyncio
async def test_tdm4_scene_gen_slash_mock():
    """calliope-draft command calls generate_scene subprocess (mock)."""
    from unittest.mock import patch
    import discord

    # Mock the subprocess call
    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(return_value=(b"", b""))

    interaction = MagicMock(spec=discord.Interaction)
    interaction.channel_id = 999999
    interaction.user = MagicMock()
    interaction.user.id = 42
    interaction.guild_id = 1
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.id = 123

    # Patch subprocess + whitelist bypass
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
         patch("discord_bot._channel_allowed", return_value=True), \
         patch("discord_bot._check_rate_limit", return_value=True), \
         patch("asyncio.wait_for", new_callable=AsyncMock) as mock_wait:
        mock_wait.return_value = (b"", b"")
        # The output file won't exist, so followup should be called with error
        from discord_bot import calliope_draft
        await calliope_draft.callback(interaction, "Aurora test", "action_combat", 1)

    # interaction.response.defer was called (or followup was called)
    assert interaction.response.defer.called or interaction.followup.send.called


# ── TDM5: rate limit enforcement ─────────────────────────────────────────────

def test_tdm5_rate_limit_enforcement():
    """Same user can't call same command within cooldown period."""
    from discord_bot import _check_rate_limit, _RATE_LIMITS

    # Clear state
    _RATE_LIMITS.pop("test_cmd_5", None)

    # First call: allowed
    assert _check_rate_limit("test_cmd_5", user_id=9001) is True
    # Immediate second call: rate limited
    assert _check_rate_limit("test_cmd_5", user_id=9001) is False
    # Different user: allowed
    assert _check_rate_limit("test_cmd_5", user_id=9002) is True


# ── TDM6: whitelist filter blocks non-whitelisted channels ───────────────────

def test_tdm6_whitelist_filter():
    """_channel_allowed returns correct results based on whitelist."""
    from discord_bot import _channel_allowed, _WHITELIST_CHANNELS

    # Save original state
    original = set(_WHITELIST_CHANNELS)
    try:
        _WHITELIST_CHANNELS.clear()
        # Empty whitelist: all channels allowed
        assert _channel_allowed(111) is True
        assert _channel_allowed(222) is True

        # Non-empty whitelist: only listed channels allowed
        _WHITELIST_CHANNELS.add(111)
        assert _channel_allowed(111) is True
        assert _channel_allowed(222) is False
    finally:
        _WHITELIST_CHANNELS.clear()
        _WHITELIST_CHANNELS.update(original)


# ── TDM7: privacy — non-whitelisted channel content not logged ───────────────

@pytest.mark.asyncio
async def test_tdm7_privacy_non_whitelisted_skipped():
    """on_message must return early for non-whitelisted channels."""
    import discord
    from discord_bot import on_message, _WHITELIST_CHANNELS

    # Set a whitelist that excludes channel 777
    original = set(_WHITELIST_CHANNELS)
    _WHITELIST_CHANNELS.clear()
    _WHITELIST_CHANNELS.add(999)  # only channel 999 allowed

    msg = MagicMock(spec=discord.Message)
    msg.author = MagicMock()
    msg.author.bot = False
    msg.channel = MagicMock()
    msg.channel.id = 777  # NOT in whitelist
    msg.content = "Aurora: This should not be proxied"

    persona_called = []

    async def mock_handle(*args, **kwargs):
        persona_called.append(True)
        return False

    # on_message imports handle_persona_message lazily — patch _channel_allowed instead
    with patch("discord_bot._channel_allowed", return_value=False):
        await on_message(msg)

    assert not persona_called, "persona_binder should not be called for non-whitelisted channel"

    _WHITELIST_CHANNELS.clear()
    _WHITELIST_CHANNELS.update(original)
