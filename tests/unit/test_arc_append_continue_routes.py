"""GAP-81: test per /api/arc/<id>/append, /summary, /threads, /continue."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.server import create_app


def _client():
    app, _ = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _make_arc(c):
    c.post("/api/arc", json={"arc_id": "arc-test-01", "title": "Arc Test", "chars": []})
    return "arc-test-01"


# ── POST /api/arc/<arc_id>/append ─────────────────────────────────────────────


def test_arc_append_missing_path_returns_400():
    c = _client()
    _make_arc(c)
    r = c.post("/api/arc/arc-test-01/append", json={})
    assert r.status_code == 400


def test_arc_append_scene_not_found_returns_400():
    c = _client()
    _make_arc(c)
    with patch("app.calliope_shell.plot_arc.append_scene", return_value=None):
        r = c.post("/api/arc/arc-test-01/append", json={"scene_md_path": "/nonexistent/path.md"})
    assert r.status_code == 400


def test_arc_append_ok_returns_200():
    c = _client()
    _make_arc(c)
    fake_result = {"arc_id": "arc-test-01", "scene": "path.md", "status": "appended"}
    with patch("app.calliope_shell.plot_arc.append_scene", return_value=fake_result):
        r = c.post("/api/arc/arc-test-01/append", json={"scene_md_path": "path.md"})
    assert r.status_code == 200
    assert r.get_json()["status"] == "appended"


# ── POST /api/arc/<arc_id>/summary ────────────────────────────────────────────


def test_arc_summary_returns_200():
    c = _client()
    _make_arc(c)
    with patch("app.calliope_shell.plot_arc.regenerate_summary", return_value="breve riassunto"):
        r = c.post("/api/arc/arc-test-01/summary", json={})
    assert r.status_code == 200


def test_arc_summary_has_summary_key():
    c = _client()
    _make_arc(c)
    with patch("app.calliope_shell.plot_arc.regenerate_summary", return_value="riassunto"):
        data = c.post("/api/arc/arc-test-01/summary", json={}).get_json()
    assert "summary" in data
    assert data["arc_id"] == "arc-test-01"


# ── GET /api/arc/<arc_id>/threads ─────────────────────────────────────────────


def test_arc_threads_returns_200():
    c = _client()
    _make_arc(c)
    with patch("app.calliope_shell.plot_arc.detect_open_threads", return_value=[]):
        r = c.get("/api/arc/arc-test-01/threads")
    assert r.status_code == 200


def test_arc_threads_has_threads_key():
    c = _client()
    _make_arc(c)
    fake_threads = [{"thread": "conflict A"}]
    with patch("app.calliope_shell.plot_arc.detect_open_threads", return_value=fake_threads):
        data = c.get("/api/arc/arc-test-01/threads").get_json()
    assert "threads" in data
    assert data["threads"] == fake_threads


# ── POST /api/arc/<arc_id>/continue ──────────────────────────────────────────


def test_arc_continue_returns_503_when_none():
    c = _client()
    _make_arc(c)
    with patch("app.calliope_shell.plot_arc.propose_next_scene", return_value=None):
        r = c.post("/api/arc/arc-test-01/continue", json={})
    assert r.status_code == 503


def test_arc_continue_ok_returns_200():
    c = _client()
    _make_arc(c)
    fake = {"proposal": "La scena continua...", "arc_id": "arc-test-01"}
    with patch("app.calliope_shell.plot_arc.propose_next_scene", return_value=fake):
        r = c.post("/api/arc/arc-test-01/continue", json={})
    assert r.status_code == 200
    assert "proposal" in r.get_json()
