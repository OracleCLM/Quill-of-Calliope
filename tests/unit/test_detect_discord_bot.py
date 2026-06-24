"""Unit test per _detect_discord_bot() in app/calliope_shell/server.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.calliope_shell.server import _detect_discord_bot

_SRV = "app.calliope_shell.server"


def _pgrep(stdout="", returncode=0):
    m = MagicMock()
    m.stdout = stdout
    m.returncode = returncode
    return m


def test_detect_bot_running_returns_up_true(monkeypatch):
    monkeypatch.setenv("CALLIOPE_DISCORD_BOT_TOKEN", "tok123")
    with patch("subprocess.run", return_value=_pgrep("12345 python scripts/discord_bot.py")):
        result = _detect_discord_bot()
    assert result["up"] is True
    assert result["reason"] == "active"


def test_detect_token_not_configured(monkeypatch):
    monkeypatch.delenv("CALLIOPE_DISCORD_BOT_TOKEN", raising=False)
    with patch("subprocess.run", return_value=_pgrep("")):
        result = _detect_discord_bot()
    assert result["up"] is False
    assert result["reason"] == "token_not_configured"
    assert result["token_configured"] is False


def test_detect_token_configured_but_not_running(monkeypatch):
    monkeypatch.setenv("CALLIOPE_DISCORD_BOT_TOKEN", "tok456")
    with patch("subprocess.run", return_value=_pgrep("")):
        result = _detect_discord_bot()
    assert result["up"] is False
    assert result["reason"] == "token_configured_but_bot_not_running"
    assert result["token_configured"] is True


def test_detect_subprocess_exception_treated_as_not_running(monkeypatch):
    monkeypatch.delenv("CALLIOPE_DISCORD_BOT_TOKEN", raising=False)
    with patch("subprocess.run", side_effect=Exception("pgrep failed")):
        result = _detect_discord_bot()
    assert result["up"] is False


def test_detect_result_has_required_keys(monkeypatch):
    monkeypatch.delenv("CALLIOPE_DISCORD_BOT_TOKEN", raising=False)
    with patch("subprocess.run", return_value=_pgrep("")):
        result = _detect_discord_bot()
    for key in ("up", "code", "latency_ms", "reason", "token_configured", "channels", "last_msg_ts"):
        assert key in result
