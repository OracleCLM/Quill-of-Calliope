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
