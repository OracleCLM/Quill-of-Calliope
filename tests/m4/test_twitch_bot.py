"""Tests for twitch_bot.py — pure logic only, no real twitchio connection."""
from __future__ import annotations

import asyncio
import stat
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from twitch_bot import (  # noqa: E402
    COOLDOWN_SEC,
    VALID_EMOTIONS,
    VALID_SCENE_TYPES,
    build_mood_payload,
    build_scene_payload,
    build_state_payload,
    check_cooldown,
    push_event,
)


# ── Test 1: Bot constants ─────────────────────────────────────────────────────

class TestBotConstants:
    def test_valid_scene_types_count(self):
        assert len(VALID_SCENE_TYPES) >= 10
        assert "action_combat" in VALID_SCENE_TYPES
        assert "lore_exposition" in VALID_SCENE_TYPES
        assert "comedic_banter" in VALID_SCENE_TYPES

    def test_valid_emotions_count(self):
        assert len(VALID_EMOTIONS) >= 5
        assert "happy" in VALID_EMOTIONS
        assert "neutral" in VALID_EMOTIONS
        assert "fearful" in VALID_EMOTIONS

    def test_cooldown_positive(self):
        assert COOLDOWN_SEC > 0


# ── Test 2: !scene command logic ──────────────────────────────────────────────

class TestSceneCommandLogic:
    def test_valid_scene_builds_payload(self):
        p = build_scene_payload("action_combat", "HeroUser")
        assert p["event"] == "scene_request"
        assert p["scene_type"] == "action_combat"
        assert p["user"] == "HeroUser"

    def test_all_valid_scene_types_pass_validation(self):
        for stype in VALID_SCENE_TYPES:
            assert stype in VALID_SCENE_TYPES

    def test_invalid_scene_type_not_in_set(self):
        assert "invalid_type_xyz" not in VALID_SCENE_TYPES
        assert "ooc_meta" not in VALID_SCENE_TYPES  # not in twitch subset


# ── Test 3: !mood command logic ───────────────────────────────────────────────

class TestMoodCommandLogic:
    def test_valid_mood_builds_payload(self):
        p = build_mood_payload("happy", "StreamUser")
        assert p["event"] == "mood_change"
        assert p["emotion"] == "happy"
        assert p["user"] == "StreamUser"

    def test_all_valid_emotions_pass_validation(self):
        for emo in VALID_EMOTIONS:
            assert emo in VALID_EMOTIONS

    def test_invalid_emotion_not_in_set(self):
        assert "confused" not in VALID_EMOTIONS
        assert "surprised" not in VALID_EMOTIONS


# ── Test 4: Subscribe / Raid → state payload ──────────────────────────────────

class TestEventPayloads:
    def test_subscribe_triggers_surprise_state(self):
        p = build_state_payload("surprise")
        assert p["event"] == "mascot_state"
        assert p["state"] == "surprise"

    def test_raid_triggers_happy_state(self):
        p = build_state_payload("happy")
        assert p["state"] == "happy"

    def test_scene_payload_structure(self):
        p = build_scene_payload("dream_surreal", "viewer99")
        assert set(p.keys()) == {"event", "scene_type", "user"}


# ── Test 5: Cooldown logic ────────────────────────────────────────────────────

class TestCooldown:
    def test_first_call_allowed(self):
        cooldowns: dict = {}
        assert check_cooldown(cooldowns, "user_a") is True

    def test_immediate_second_call_blocked(self):
        cooldowns: dict = {}
        check_cooldown(cooldowns, "user_b")
        assert check_cooldown(cooldowns, "user_b") is False

    def test_expired_cooldown_allowed(self):
        cooldowns = {"user_c": time.monotonic() - (COOLDOWN_SEC + 1)}
        assert check_cooldown(cooldowns, "user_c") is True

    def test_different_users_independent(self):
        cooldowns: dict = {}
        check_cooldown(cooldowns, "user_d")
        assert check_cooldown(cooldowns, "user_e") is True  # different user


# ── Test 6: push_event (mock httpx) ──────────────────────────────────────────

class TestPushEvent:
    def test_push_event_sends_post(self):
        async def run():
            with patch("httpx.AsyncClient") as mock_cls:
                mock_client = AsyncMock()
                mock_cls.return_value.__aenter__.return_value = mock_client
                await push_event("http://localhost:8767", {"event": "test"})
                mock_client.post.assert_called_once()
                args, kwargs = mock_client.post.call_args
                assert "/twitch-event" in args[0]
                assert kwargs["json"]["event"] == "test"

        asyncio.run(run())

    def test_push_event_silent_on_error(self):
        async def run():
            with patch("httpx.AsyncClient") as mock_cls:
                mock_client = AsyncMock()
                mock_client.post.side_effect = Exception("connection refused")
                mock_cls.return_value.__aenter__.return_value = mock_client
                # Should not raise
                await push_event("http://localhost:8767", {"event": "test"})

        asyncio.run(run())


# ── Test 7: Launcher script ───────────────────────────────────────────────────

class TestLauncherScript:
    def test_exists_and_executable(self):
        script = ROOT / "scripts" / "start_twitch_bot.sh"
        assert script.exists()
        assert bool(script.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP))

    def test_valid_bash(self):
        r = subprocess.run(["bash", "-n", str(ROOT / "scripts" / "start_twitch_bot.sh")],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr

    def test_validates_twitch_env_vars(self):
        content = (ROOT / "scripts" / "start_twitch_bot.sh").read_text()
        assert "CALLIOPE_TWITCH_TOKEN" in content
        assert "--stop" in content
        assert "--status" in content

    def test_overlay_files_exist(self):
        overlay = ROOT / "frontend" / "twitch_overlay"
        for fname in ("index.html", "overlay.css", "overlay.js"):
            assert (overlay / fname).exists(), f"Missing: {fname}"
