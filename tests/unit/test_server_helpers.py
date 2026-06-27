"""GAP-62: test per _detect_discord_bot e _load_emotion_map in server.py."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import yaml

from app.calliope_shell.server import _detect_discord_bot, _load_emotion_map


# ── _load_emotion_map ─────────────────────────────────────────────────────────


def test_load_emotion_map_returns_dict_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.calliope_shell.server.Path",
        lambda *a: tmp_path / "nonexistent.yaml",
    )
    result = _load_emotion_map()
    assert isinstance(result, dict)


def test_load_emotion_map_parses_yaml(tmp_path, monkeypatch):
    emotion_file = tmp_path / "calliope_emotion_map.yaml"
    emotion_file.write_text(yaml.dump({"joy": "😊", "anger": "😠"}), encoding="utf-8")
    import app.calliope_shell.server as srv
    monkeypatch.setattr(srv, "_load_emotion_map", lambda: yaml.safe_load(emotion_file.read_text()))
    result = srv._load_emotion_map()
    assert result["joy"] == "😊"
    assert result["anger"] == "😠"


def test_load_emotion_map_empty_file_returns_empty_dict(tmp_path, monkeypatch):
    emotion_file = tmp_path / "calliope_emotion_map.yaml"
    emotion_file.write_text("", encoding="utf-8")
    import app.calliope_shell.server as srv
    monkeypatch.setattr(srv, "_load_emotion_map", lambda: yaml.safe_load(emotion_file.read_text()) or {})
    result = srv._load_emotion_map()
    assert result == {}


# ── _detect_discord_bot ───────────────────────────────────────────────────────


def test_detect_bot_no_token_returns_not_configured(monkeypatch):
    monkeypatch.delenv("CALLIOPE_DISCORD_BOT_TOKEN", raising=False)
    mock_proc = MagicMock()
    mock_proc.stdout = ""
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock_proc)
    result = _detect_discord_bot()
    assert result["up"] is False
    assert result["token_configured"] is False
    assert result["reason"] == "token_not_configured"


def test_detect_bot_token_configured_but_not_running(monkeypatch):
    monkeypatch.setenv("CALLIOPE_DISCORD_BOT_TOKEN", "fake-token-123")
    mock_proc = MagicMock()
    mock_proc.stdout = ""
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock_proc)
    result = _detect_discord_bot()
    assert result["up"] is False
    assert result["token_configured"] is True
    assert result["reason"] == "token_configured_but_bot_not_running"


def test_detect_bot_running_returns_active(monkeypatch):
    monkeypatch.setenv("CALLIOPE_DISCORD_BOT_TOKEN", "fake-token-123")
    mock_proc = MagicMock()
    mock_proc.stdout = "12345 python scripts/discord_bot.py"
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock_proc)
    result = _detect_discord_bot()
    assert result["up"] is True
    assert result["reason"] == "active"


def test_detect_bot_result_has_required_keys(monkeypatch):
    monkeypatch.delenv("CALLIOPE_DISCORD_BOT_TOKEN", raising=False)
    mock_proc = MagicMock()
    mock_proc.stdout = ""
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock_proc)
    result = _detect_discord_bot()
    for key in ("up", "reason", "token_configured", "channels", "last_msg_ts"):
        assert key in result


def test_detect_bot_subprocess_exception_gracefully_handled(monkeypatch):
    monkeypatch.setenv("CALLIOPE_DISCORD_BOT_TOKEN", "tok")

    def raise_timeout(*a, **kw):
        raise TimeoutError("pgrep timeout")

    monkeypatch.setattr("subprocess.run", raise_timeout)
    result = _detect_discord_bot()
    assert isinstance(result, dict)
    assert result["up"] is False
