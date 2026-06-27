"""GAP-45: test unitari per discord_live — _load_env, build_dce_command, run_live_export."""

import sys
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from app.calliope_shell.discord_live import (
    DceError,
    _load_env_file,
    build_dce_command,
    dce_available,
    dce_path,
    run_live_export,
)


# ── _load_env_file ────────────────────────────────────────────────────────────


def test_load_env_file_missing_returns_empty(tmp_path):
    result = _load_env_file(tmp_path / "no_file.env")
    assert result == {}


def test_load_env_file_parses_key_value(tmp_path):
    f = tmp_path / ".env"
    f.write_text("TOKEN=abc123\nGUILD=987\n", encoding="utf-8")
    result = _load_env_file(f)
    assert result["TOKEN"] == "abc123"
    assert result["GUILD"] == "987"


def test_load_env_file_ignores_comments(tmp_path):
    f = tmp_path / ".env"
    f.write_text("# commento\nKEY=val\n", encoding="utf-8")
    result = _load_env_file(f)
    assert "# commento" not in result
    assert result["KEY"] == "val"


def test_load_env_file_ignores_blank_lines(tmp_path):
    f = tmp_path / ".env"
    f.write_text("\n\nA=1\n\n", encoding="utf-8")
    result = _load_env_file(f)
    assert result == {"A": "1"}


def test_load_env_file_first_equals_only(tmp_path):
    f = tmp_path / ".env"
    f.write_text("URL=http://host:8080/path?x=1\n", encoding="utf-8")
    result = _load_env_file(f)
    assert result["URL"] == "http://host:8080/path?x=1"


# ── dce_path ──────────────────────────────────────────────────────────────────


def test_dce_path_env_override(monkeypatch):
    monkeypatch.setenv("DCE_BIN", "/opt/tools/dce")
    assert dce_path() == "/opt/tools/dce"


def test_dce_path_default_without_env(monkeypatch):
    monkeypatch.delenv("DCE_BIN", raising=False)
    result = dce_path()
    assert "dce" in result


# ── dce_available ─────────────────────────────────────────────────────────────


def test_dce_available_false_for_nonexistent(tmp_path):
    fake = str(tmp_path / "dce_nonexistent")
    with patch("shutil.which", return_value=None):
        assert dce_available(fake) is False


def test_dce_available_true_for_executable(tmp_path):
    f = tmp_path / "dce"
    f.write_text("#!/bin/sh\n")
    f.chmod(0o755)
    assert dce_available(str(f)) is True


# ── build_dce_command ─────────────────────────────────────────────────────────


def test_build_dce_command_basic():
    cmd = build_dce_command(["ch1"], "/out", token="tok", binary="/usr/bin/dce")
    assert "/usr/bin/dce" in cmd
    assert "exportchannel" in cmd
    assert "-t" in cmd
    assert "tok" in cmd
    assert "-c" in cmd
    assert "ch1" in cmd
    assert "/out" in cmd


def test_build_dce_command_multiple_channels():
    cmd = build_dce_command(["ch1", "ch2", "ch3"], "/out", token="tok", binary="dce")
    c_idx = [i for i, v in enumerate(cmd) if v == "-c"]
    assert len(c_idx) == 3


def test_build_dce_command_after_before():
    cmd = build_dce_command(["ch1"], "/out", token="tok", binary="dce",
                            after="2024-01-01", before="2024-06-01")
    assert "--after" in cmd
    assert "2024-01-01" in cmd
    assert "--before" in cmd
    assert "2024-06-01" in cmd


def test_build_dce_command_no_date_no_flags():
    cmd = build_dce_command(["ch1"], "/out", token="tok", binary="dce")
    assert "--after" not in cmd
    assert "--before" not in cmd


def test_build_dce_command_json_format():
    cmd = build_dce_command(["ch1"], "/out", token="tok", binary="dce")
    assert "-f" in cmd
    idx = cmd.index("-f")
    assert cmd[idx + 1] == "Json"


# ── run_live_export ───────────────────────────────────────────────────────────


def _mock_proc(returncode=0, stderr=""):
    return SimpleNamespace(returncode=returncode, stderr=stderr)


def test_run_live_export_no_channels_raises():
    with pytest.raises(DceError, match="nessun channel_id"):
        run_live_export([], "/out", token_env="DISCORD_USER_TOKEN")


def test_run_live_export_missing_binary_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("DISCORD_USER_TOKEN", "tok")
    with patch("app.calliope_shell.discord_live.dce_available", return_value=False):
        with pytest.raises(DceError, match="non trovato"):
            run_live_export(["ch1"], str(tmp_path), token_env="DISCORD_USER_TOKEN",
                            binary="/fake/dce")


def test_run_live_export_missing_token_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_USER_TOKEN", raising=False)
    with patch("app.calliope_shell.discord_live.dce_available", return_value=True):
        with patch("app.calliope_shell.discord_live._get_secret", return_value=None):
            with pytest.raises(DceError, match="token"):
                run_live_export(["ch1"], str(tmp_path), token_env="DISCORD_USER_TOKEN",
                                binary="/fake/dce")


def test_run_live_export_dce_nonzero_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("DISCORD_USER_TOKEN", "tok")
    bad_runner = MagicMock(return_value=_mock_proc(returncode=1, stderr="Error!"))
    with patch("app.calliope_shell.discord_live.dce_available", return_value=True):
        with pytest.raises(DceError, match="fallito"):
            run_live_export(["ch1"], str(tmp_path), token_env="DISCORD_USER_TOKEN",
                            binary="/fake/dce", _runner=bad_runner)


def test_run_live_export_success_returns_json_files(tmp_path, monkeypatch):
    monkeypatch.setenv("DISCORD_USER_TOKEN", "tok")
    (tmp_path / "out.json").write_text("{}", encoding="utf-8")
    ok_runner = MagicMock(return_value=_mock_proc(returncode=0))
    with patch("app.calliope_shell.discord_live.dce_available", return_value=True):
        result = run_live_export(["ch1"], str(tmp_path), token_env="DISCORD_USER_TOKEN",
                                 binary="/fake/dce", _runner=ok_runner)
    assert len(result) == 1
    assert result[0].name == "out.json"


def test_run_live_export_timeout_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("DISCORD_USER_TOKEN", "tok")

    def timeout_runner(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=[], timeout=1)

    with patch("app.calliope_shell.discord_live.dce_available", return_value=True):
        with pytest.raises(DceError, match="timeout"):
            run_live_export(["ch1"], str(tmp_path), token_env="DISCORD_USER_TOKEN",
                            binary="/fake/dce", _runner=timeout_runner)


def test_run_live_export_file_not_found_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("DISCORD_USER_TOKEN", "tok")

    def fnf_runner(*args, **kwargs):
        raise FileNotFoundError("dce not found")

    with patch("app.calliope_shell.discord_live.dce_available", return_value=True):
        with pytest.raises(DceError, match="impossibile"):
            run_live_export(["ch1"], str(tmp_path), token_env="DISCORD_USER_TOKEN",
                            binary="/fake/dce", _runner=fnf_runner)
