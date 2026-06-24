"""Unit test per scripts/discord_bot._channel_allowed e _check_channel_rate."""
from __future__ import annotations

import sys
import time
from unittest.mock import MagicMock

import pytest

pytest.importorskip("audioop")

sys.modules.setdefault("discord", MagicMock())
sys.modules.setdefault("discord.app_commands", MagicMock())
sys.modules.setdefault("aiohttp", MagicMock())

import scripts.discord_bot as discord_bot  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_state():
    discord_bot._CHANNEL_MSG_RATE.clear()
    yield
    discord_bot._CHANNEL_MSG_RATE.clear()


# ── _channel_allowed ──────────────────────────────────────────────────────────

def test_channel_allowed_empty_whitelist(monkeypatch):
    monkeypatch.setattr(discord_bot, "_WHITELIST_CHANNELS", set())
    assert discord_bot._channel_allowed(12345) is True
    assert discord_bot._channel_allowed(99999) is True


def test_channel_allowed_in_whitelist(monkeypatch):
    monkeypatch.setattr(discord_bot, "_WHITELIST_CHANNELS", {100, 200})
    assert discord_bot._channel_allowed(100) is True
    assert discord_bot._channel_allowed(200) is True


def test_channel_not_in_whitelist(monkeypatch):
    monkeypatch.setattr(discord_bot, "_WHITELIST_CHANNELS", {100, 200})
    assert discord_bot._channel_allowed(999) is False


# ── _check_channel_rate ───────────────────────────────────────────────────────

def test_check_channel_rate_first_call_allowed():
    assert discord_bot._check_channel_rate(777) is True


def test_check_channel_rate_records_timestamp():
    discord_bot._check_channel_rate(888)
    assert len(discord_bot._CHANNEL_MSG_RATE[888]) == 1


def test_check_channel_rate_blocks_at_limit(monkeypatch):
    monkeypatch.setattr(discord_bot, "_MAX_MSG_PER_MIN", 3)
    now = time.time()
    discord_bot._CHANNEL_MSG_RATE[555] = [now - 5, now - 10, now - 15]
    assert discord_bot._check_channel_rate(555) is False


def test_check_channel_rate_allows_after_stale_eviction(monkeypatch):
    monkeypatch.setattr(discord_bot, "_MAX_MSG_PER_MIN", 3)
    now = time.time()
    # tutti i timestamp sono scaduti (>60s)
    discord_bot._CHANNEL_MSG_RATE[444] = [now - 120, now - 90, now - 75]
    assert discord_bot._check_channel_rate(444) is True
