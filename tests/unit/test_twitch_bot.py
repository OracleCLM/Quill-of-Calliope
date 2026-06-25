"""Unit test per scripts/twitch_bot.py — funzioni pure (no twitchio)."""
from __future__ import annotations

import sys
import time
from unittest.mock import MagicMock

sys.modules.setdefault("twitchio", MagicMock())
sys.modules.setdefault("twitchio.ext", MagicMock())
sys.modules.setdefault("twitchio.ext.commands", MagicMock())

from scripts.twitch_bot import (  # noqa: E402
    VALID_EMOTIONS,
    VALID_SCENE_TYPES,
    build_mood_payload,
    build_scene_payload,
    build_state_payload,
    check_cooldown,
)


def test_valid_scene_types_is_frozenset() -> None:
    assert isinstance(VALID_SCENE_TYPES, frozenset)
    assert "action_combat" in VALID_SCENE_TYPES


def test_valid_emotions_is_frozenset() -> None:
    assert isinstance(VALID_EMOTIONS, frozenset)
    assert "neutral" in VALID_EMOTIONS


def test_build_scene_payload_structure() -> None:
    result = build_scene_payload("action_combat", "test_user")
    assert result == {"event": "scene_request", "scene_type": "action_combat", "user": "test_user"}


def test_build_scene_payload_custom_values() -> None:
    result = build_scene_payload("lore_exposition", "another_user")
    assert result["event"] == "scene_request"
    assert result["scene_type"] == "lore_exposition"
    assert result["user"] == "another_user"


def test_build_mood_payload_structure() -> None:
    result = build_mood_payload("happy", "test_user")
    assert result == {"event": "mood_change", "emotion": "happy", "user": "test_user"}


def test_build_mood_payload_custom_values() -> None:
    result = build_mood_payload("sad", "mood_user")
    assert result["event"] == "mood_change"
    assert result["emotion"] == "sad"
    assert result["user"] == "mood_user"


def test_build_state_payload_structure() -> None:
    result = build_state_payload("idle")
    assert result == {"event": "mascot_state", "state": "idle"}


def test_build_state_payload_custom_values() -> None:
    result = build_state_payload("dancing")
    assert result["event"] == "mascot_state"
    assert result["state"] == "dancing"


def test_check_cooldown_initial_call_returns_true() -> None:
    cooldowns: dict = {}
    assert check_cooldown(cooldowns, "user1") is True
    assert "user1" in cooldowns


def test_check_cooldown_second_call_returns_false() -> None:
    cooldowns: dict = {}
    check_cooldown(cooldowns, "user2", cooldown_sec=5.0)
    assert check_cooldown(cooldowns, "user2", cooldown_sec=5.0) is False


def test_check_cooldown_expired_returns_true() -> None:
    cooldowns: dict = {"user3": time.monotonic() - 10.0}
    assert check_cooldown(cooldowns, "user3", cooldown_sec=5.0) is True


def test_check_cooldown_updates_timestamp_on_success() -> None:
    old_time = time.monotonic() - 10.0
    cooldowns: dict = {"user4": old_time}
    check_cooldown(cooldowns, "user4", cooldown_sec=5.0)
    assert cooldowns["user4"] > old_time


# ── push_event / _make_bot / main ─────────────────────────────────────────────

import asyncio  # noqa: E402
from unittest.mock import AsyncMock, patch  # noqa: E402 (MagicMock already imported)

import pytest  # noqa: E402

from scripts.twitch_bot import _make_bot, main, push_event  # noqa: E402


def test_push_event_success():
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    with patch("scripts.twitch_bot.httpx.AsyncClient", return_value=mock_client):
        asyncio.run(push_event("http://localhost:8767", {"event": "test"}))
    mock_client.post.assert_awaited_once()


def test_push_event_exception_silent(capsys):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post.side_effect = Exception("connection refused")
    with patch("scripts.twitch_bot.httpx.AsyncClient", return_value=mock_client):
        asyncio.run(push_event("http://localhost:8767", {}))
    assert "push_event failed" in capsys.readouterr().out


# Helper: build CalliopeBot with a plain (non-MagicMock) base class so that
# the class's own async methods are accessible without MagicMock shadowing.
def _get_real_bot():
    class FakeBot:
        def __init__(self, **kwargs):
            pass
        async def handle_commands(self, message):
            pass

    fake_cmds = type("fake_cmds", (), {
        "Bot": FakeBot,
        "Context": MagicMock,
        "command": lambda *a, **kw: lambda f: f,  # passthrough — keeps coroutine
    })()
    with patch.dict(__import__("sys").modules, {"twitchio.ext.commands": fake_cmds}):
        return _make_bot("cid", "csec", "bid", "mychan", "http://localhost:8767")


def test_event_ready(capsys):
    bot = _get_real_bot()
    asyncio.run(type(bot).__dict__["event_ready"](bot))
    assert "Ready" in capsys.readouterr().out


def test_event_message_echo():
    bot = _get_real_bot()
    msg = MagicMock()
    msg.echo = True
    bot.handle_commands = AsyncMock()
    asyncio.run(type(bot).__dict__["event_message"](bot, msg))
    bot.handle_commands.assert_not_awaited()


def test_event_message_normal():
    bot = _get_real_bot()
    msg = MagicMock()
    msg.echo = False
    bot.handle_commands = AsyncMock()
    asyncio.run(type(bot).__dict__["event_message"](bot, msg))
    bot.handle_commands.assert_awaited_once_with(msg)


def test_scene_no_type():
    bot = _get_real_bot()
    ctx = MagicMock()
    ctx.send = AsyncMock()
    asyncio.run(type(bot).__dict__["scene"](bot, ctx, scene_type=None))
    ctx.send.assert_awaited_once()
    assert "Usage" in ctx.send.call_args[0][0]


def test_scene_invalid_type():
    bot = _get_real_bot()
    ctx = MagicMock()
    ctx.send = AsyncMock()
    asyncio.run(type(bot).__dict__["scene"](bot, ctx, scene_type="invalid_type"))
    ctx.send.assert_awaited_once()
    assert "Unknown" in ctx.send.call_args[0][0]


def test_scene_on_cooldown():
    bot = _get_real_bot()
    ctx = MagicMock()
    ctx.send = AsyncMock()
    ctx.author.display_name = "TestUser"
    ctx.author.id = "42"
    bot._cooldowns["42"] = time.monotonic()
    asyncio.run(type(bot).__dict__["scene"](bot, ctx, scene_type="action_combat"))
    assert "wait" in ctx.send.call_args[0][0].lower()


def test_scene_success():
    bot = _get_real_bot()
    ctx = MagicMock()
    ctx.send = AsyncMock()
    ctx.author.display_name = "HeroUser"
    ctx.author.id = "99"
    with patch("scripts.twitch_bot.push_event", new_callable=AsyncMock):
        asyncio.run(type(bot).__dict__["scene"](bot, ctx, scene_type="action_combat"))
    assert "HeroUser" in ctx.send.call_args[0][0]


def test_mood_no_emotion():
    bot = _get_real_bot()
    ctx = MagicMock()
    ctx.send = AsyncMock()
    asyncio.run(type(bot).__dict__["mood"](bot, ctx, emotion=None))
    sent = ctx.send.call_args[0][0]
    assert "Usage" in sent or "options" in sent


def test_mood_invalid():
    bot = _get_real_bot()
    ctx = MagicMock()
    ctx.send = AsyncMock()
    asyncio.run(type(bot).__dict__["mood"](bot, ctx, emotion="rage"))
    assert "Invalid" in ctx.send.call_args[0][0]


def test_mood_on_cooldown():
    bot = _get_real_bot()
    ctx = MagicMock()
    ctx.send = AsyncMock()
    ctx.author.id = "77"
    bot._cooldowns["77"] = time.monotonic()
    asyncio.run(type(bot).__dict__["mood"](bot, ctx, emotion="happy"))
    assert "wait" in ctx.send.call_args[0][0].lower()


def test_mood_success():
    bot = _get_real_bot()
    ctx = MagicMock()
    ctx.send = AsyncMock()
    ctx.author.display_name = "MoodUser"
    ctx.author.id = "55"
    with patch("scripts.twitch_bot.push_event", new_callable=AsyncMock):
        asyncio.run(type(bot).__dict__["mood"](bot, ctx, emotion="happy"))
    assert "happy" in ctx.send.call_args[0][0]


def test_event_usernotice_missing_channel():
    bot = _get_real_bot()
    notice = MagicMock()
    notice.channel = None
    notice.user = MagicMock()
    asyncio.run(type(bot).__dict__["event_usernotice"](bot, notice))


def test_event_usernotice_sub():
    bot = _get_real_bot()
    notice = MagicMock()
    notice.channel.send = AsyncMock()
    notice.user.display_name = "SubUser"
    notice.tags = {"msg-id": "sub"}
    with patch("scripts.twitch_bot.push_event", new_callable=AsyncMock) as mp:
        asyncio.run(type(bot).__dict__["event_usernotice"](bot, notice))
    mp.assert_awaited_once()
    notice.channel.send.assert_awaited_once()
    assert "subscriber" in notice.channel.send.call_args[0][0].lower()


def test_event_usernotice_raid():
    bot = _get_real_bot()
    notice = MagicMock()
    notice.channel.send = AsyncMock()
    notice.user.display_name = "Raider"
    notice.tags = {"msg-id": "raid", "msg-param-viewerCount": "42"}
    with patch("scripts.twitch_bot.push_event", new_callable=AsyncMock) as mp:
        asyncio.run(type(bot).__dict__["event_usernotice"](bot, notice))
    mp.assert_awaited_once()
    notice.channel.send.assert_awaited_once()
    assert "42" in notice.channel.send.call_args[0][0]


def test_event_usernotice_unknown():
    bot = _get_real_bot()
    notice = MagicMock()
    notice.channel.send = AsyncMock()
    notice.tags = {"msg-id": "bits"}
    with patch("scripts.twitch_bot.push_event", new_callable=AsyncMock) as mp:
        asyncio.run(type(bot).__dict__["event_usernotice"](bot, notice))
    mp.assert_not_awaited()


def test_main_missing_env_vars(monkeypatch):
    for k in [
        "CALLIOPE_TWITCH_CLIENT_ID", "CALLIOPE_TWITCH_CLIENT_SECRET",
        "CALLIOPE_TWITCH_BOT_ID", "CALLIOPE_TWITCH_CHANNEL",
    ]:
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


def test_main_all_env_vars_set(monkeypatch):
    monkeypatch.setenv("CALLIOPE_TWITCH_CLIENT_ID", "cid")
    monkeypatch.setenv("CALLIOPE_TWITCH_CLIENT_SECRET", "csec")
    monkeypatch.setenv("CALLIOPE_TWITCH_BOT_ID", "bid")
    monkeypatch.setenv("CALLIOPE_TWITCH_CHANNEL", "mychannel")
    mock_bot = MagicMock()
    with patch("scripts.twitch_bot._make_bot", return_value=mock_bot):
        main()
    mock_bot.run.assert_called_once()
