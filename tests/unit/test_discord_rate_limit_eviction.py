"""Regression tests for P0 #3 — unbounded memory growth in discord_bot rate-limit.

Audit ref: docs/audit/CALLIOPE_DEEP_REVIEW_2026-05-22.md §2 P0 #3
Fix: _cleanup_rate_state evicts stale users/channels from _RATE_LIMITS and
_CHANNEL_MSG_RATE; called opportunistically every _CLEANUP_INTERVAL.
"""
import pytest
pytest.importorskip("audioop")

import sys
import time
from unittest.mock import MagicMock  # noqa: E402

import pytest

# discord-py and aiohttp not in test env; stub before importing discord_bot.
# tests/discord/__init__.py shadows the 'discord' library namespace under pytest,
# so we pre-populate sys.modules to bypass the import error.
sys.modules.setdefault("discord", MagicMock())
sys.modules.setdefault("discord.app_commands", MagicMock())
sys.modules.setdefault("aiohttp", MagicMock())

import scripts.discord_bot as discord_bot  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_state():
    discord_bot._RATE_LIMITS.clear()
    discord_bot._CHANNEL_MSG_RATE.clear()
    discord_bot._last_cleanup = 0.0
    yield
    discord_bot._RATE_LIMITS.clear()
    discord_bot._CHANNEL_MSG_RATE.clear()


def test_cleanup_evicts_stale_users():
    now_mono = time.monotonic()
    discord_bot._RATE_LIMITS["test_cmd"] = {
        i: now_mono - (discord_bot._RATE_LIMIT_TTL + 5) for i in range(500)
    }
    discord_bot._cleanup_rate_state(force=True)
    assert "test_cmd" not in discord_bot._RATE_LIMITS


def test_cleanup_keeps_fresh_users():
    now_mono = time.monotonic()
    discord_bot._RATE_LIMITS["fresh_cmd"] = {
        1: now_mono - 1.0,
        2: now_mono - 2.0,
    }
    discord_bot._cleanup_rate_state(force=True)
    assert discord_bot._RATE_LIMITS["fresh_cmd"] == {1: pytest.approx(now_mono - 1.0, abs=0.5),
                                                     2: pytest.approx(now_mono - 2.0, abs=0.5)}


def test_cleanup_drops_empty_channel_buckets():
    now_wall = time.time()
    discord_bot._CHANNEL_MSG_RATE[12345] = [now_wall - 120, now_wall - 200]
    discord_bot._CHANNEL_MSG_RATE[67890] = [now_wall - 5, now_wall - 10]
    discord_bot._cleanup_rate_state(force=True)
    assert 12345 not in discord_bot._CHANNEL_MSG_RATE
    assert 67890 in discord_bot._CHANNEL_MSG_RATE
    assert len(discord_bot._CHANNEL_MSG_RATE[67890]) == 2


def test_cleanup_throttled_by_interval():
    now_mono = time.monotonic()
    discord_bot._last_cleanup = now_mono
    discord_bot._RATE_LIMITS["stale"] = {1: now_mono - 999.0}
    discord_bot._cleanup_rate_state(force=False)
    assert "stale" in discord_bot._RATE_LIMITS


def test_check_rate_limit_triggers_cleanup_after_interval():
    now_mono = time.monotonic()
    discord_bot._RATE_LIMITS["old_cmd"] = {
        i: now_mono - (discord_bot._RATE_LIMIT_TTL + 1) for i in range(100)
    }
    discord_bot._last_cleanup = now_mono - (discord_bot._CLEANUP_INTERVAL + 1)
    discord_bot._check_rate_limit("new_cmd", 42)
    assert "old_cmd" not in discord_bot._RATE_LIMITS


def test_unbounded_growth_prevented():
    """After many users + cleanup, dict size stays bounded by fresh entries only."""
    now_mono = time.monotonic()
    discord_bot._RATE_LIMITS["spam"] = {
        i: now_mono - (discord_bot._RATE_LIMIT_TTL + 10) for i in range(10_000)
    }
    discord_bot._cleanup_rate_state(force=True)
    total = sum(len(users) for users in discord_bot._RATE_LIMITS.values())
    assert total == 0
