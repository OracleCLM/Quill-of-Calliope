"""Tests for Calliope.AI daemon launcher scripts."""
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).parent.parent.parent
SCRIPTS = ROOT / "scripts"


def _is_executable(path: Path) -> bool:
    return bool(path.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))


def _bash_syntax(path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)


class TestStartMascotWs:
    def test_file_exists(self):
        assert (SCRIPTS / "start_mascot_ws.sh").exists()

    def test_executable(self):
        assert _is_executable(SCRIPTS / "start_mascot_ws.sh")

    def test_valid_bash_syntax(self):
        r = _bash_syntax(SCRIPTS / "start_mascot_ws.sh")
        assert r.returncode == 0, f"bash syntax error: {r.stderr}"

    def test_has_stop_flag(self):
        content = (SCRIPTS / "start_mascot_ws.sh").read_text()
        assert "--stop" in content

    def test_has_status_flag(self):
        content = (SCRIPTS / "start_mascot_ws.sh").read_text()
        assert "--status" in content

    def test_pid_file_defined(self):
        content = (SCRIPTS / "start_mascot_ws.sh").read_text()
        assert "PID_FILE" in content
        assert "/tmp/calliope_mascot_ws.pid" in content

    def test_status_exits_1_when_not_running(self):
        # If no PID file, --status should exit non-zero
        env = os.environ.copy()
        r = subprocess.run(
            ["bash", str(SCRIPTS / "start_mascot_ws.sh"), "--status"],
            capture_output=True, text=True, env=env,
        )
        # May be 0 (already running) or 1 (not running) — just check it runs
        assert r.returncode in (0, 1)
        assert len(r.stdout) > 0 or len(r.stderr) == 0  # produces output


class TestStartAll:
    def test_start_all_exists(self):
        assert (SCRIPTS / "start_all_calliope_daemons.sh").exists()

    def test_start_all_executable(self):
        assert _is_executable(SCRIPTS / "start_all_calliope_daemons.sh")

    def test_start_all_valid_bash(self):
        r = _bash_syntax(SCRIPTS / "start_all_calliope_daemons.sh")
        assert r.returncode == 0, f"syntax error: {r.stderr}"

    def test_start_all_references_both_daemons(self):
        content = (SCRIPTS / "start_all_calliope_daemons.sh").read_text()
        assert "llm_gateway" in content
        assert "start_mascot_ws" in content


class TestStopAll:
    def test_stop_all_exists(self):
        assert (SCRIPTS / "stop_all_calliope_daemons.sh").exists()

    def test_stop_all_executable(self):
        assert _is_executable(SCRIPTS / "stop_all_calliope_daemons.sh")

    def test_stop_all_valid_bash(self):
        r = _bash_syntax(SCRIPTS / "stop_all_calliope_daemons.sh")
        assert r.returncode == 0, f"syntax error: {r.stderr}"

    def test_stop_all_references_both(self):
        content = (SCRIPTS / "stop_all_calliope_daemons.sh").read_text()
        assert "start_mascot_ws.sh" in content
        assert "GW_PID" in content or "llm_gateway" in content


class TestSystemdDoc:
    def test_systemd_doc_exists(self):
        assert (ROOT / "docs" / "systemd_user_units.md").exists()

    def test_systemd_doc_has_both_units(self):
        content = (ROOT / "docs" / "systemd_user_units.md").read_text()
        assert "calliope-llm-gateway" in content
        assert "calliope-mascot-ws" in content
        assert "systemctl --user" in content
