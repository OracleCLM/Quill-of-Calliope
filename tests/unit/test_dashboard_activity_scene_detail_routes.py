"""GAP-79: test per /api/dashboard/activity, /api/chars/<name>/memory, /api/scenes/<scene_id>."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.server import create_app


def _client():
    app, _ = create_app()
    app.config["TESTING"] = True
    return app.test_client()


# ── GET /api/dashboard/activity ───────────────────────────────────────────────


def test_dashboard_activity_returns_200():
    r = _client().get("/api/dashboard/activity")
    assert r.status_code == 200


def test_dashboard_activity_has_required_keys():
    data = _client().get("/api/dashboard/activity").get_json()
    assert "events" in data
    assert "mode" in data
    assert "count" in data


def test_dashboard_activity_default_mode_is_highlight():
    data = _client().get("/api/dashboard/activity").get_json()
    assert data["mode"] == "highlight"


def test_dashboard_activity_verbose_mode_ok():
    data = _client().get("/api/dashboard/activity?mode=verbose").get_json()
    assert data["mode"] == "verbose"


def test_dashboard_activity_invalid_mode_returns_400():
    r = _client().get("/api/dashboard/activity?mode=INVALID")
    assert r.status_code == 400


def test_dashboard_activity_limit_respected():
    data = _client().get("/api/dashboard/activity?limit=3").get_json()
    assert data["limit"] == 3


# ── GET /api/chars/<name>/memory ──────────────────────────────────────────────


def test_chars_memory_returns_200():
    r = _client().get("/api/chars/Aurora/memory")
    assert r.status_code == 200


def test_chars_memory_has_name_field():
    data = _client().get("/api/chars/Aurora/memory").get_json()
    assert data["name"] == "Aurora"


def test_chars_memory_has_snippets_field():
    data = _client().get("/api/chars/Aurora/memory").get_json()
    assert "snippets" in data
    assert isinstance(data["snippets"], list)


def test_chars_memory_graceful_without_chromadb():
    data = _client().get("/api/chars/CharInesistente9999/memory").get_json()
    assert "snippets" in data


# ── GET /api/scenes/<scene_id> ────────────────────────────────────────────────


def test_scene_detail_not_found_returns_404():
    r = _client().get("/api/db/scenes/scena-inesistente-xyz-9999")
    assert r.status_code == 404


def test_scene_detail_found_returns_200():
    client = _client()
    resp = client.post("/api/db/scenes", json={"title": "Scena Test"})
    assert resp.status_code == 201
    scene_id = resp.get_json()["id"]
    r = client.get(f"/api/db/scenes/{scene_id}")
    assert r.status_code == 200


def test_scene_detail_found_returns_title():
    client = _client()
    resp = client.post("/api/db/scenes", json={"title": "Scena Magica"})
    scene_id = resp.get_json()["id"]
    data = client.get(f"/api/db/scenes/{scene_id}").get_json()
    assert data.get("scene", {}).get("title") == "Scena Magica"
