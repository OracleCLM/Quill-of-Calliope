"""Unit test per route GET/POST /api/dashboard/* di server.py."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.calliope_shell.server import create_app

_SRV = "app.calliope_shell.server"
_AUDIT = "app.calliope_shell.audit_trail.recent_events"


@pytest.fixture()
def client():
    app, _ = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── GET /api/dashboard/llm_routing ───────────────────────────────────────────

def test_llm_routing_get_200(client):
    rv = client.get("/api/dashboard/llm_routing")
    assert rv.status_code == 200


def test_llm_routing_get_has_required_keys(client):
    data = client.get("/api/dashboard/llm_routing").get_json()
    expected = {
        "active_provider", "active_model", "uncensored_active",
        "uncensored_provider", "uncensored_model",
        "default_provider", "default_model",
    }
    assert expected.issubset(data.keys())


def test_llm_routing_get_types(client):
    data = client.get("/api/dashboard/llm_routing").get_json()
    assert isinstance(data["active_provider"], str)
    assert isinstance(data["uncensored_active"], bool)


# ── POST /api/dashboard/llm_routing ──────────────────────────────────────────

def test_llm_routing_post_enable_uncensored(client):
    rv = client.post("/api/dashboard/llm_routing", json={"uncensored": True})
    assert rv.status_code == 200
    assert rv.get_json()["uncensored_active"] is True


def test_llm_routing_post_disable_uncensored(client):
    rv = client.post("/api/dashboard/llm_routing", json={"uncensored": False})
    assert rv.status_code == 200
    assert rv.get_json()["uncensored_active"] is False


def test_llm_routing_post_missing_key_400(client):
    rv = client.post("/api/dashboard/llm_routing", json={})
    assert rv.status_code == 400
    assert rv.get_json() == {"error": "missing 'uncensored' (bool) in body"}


# ── GET /api/dashboard/activity ───────────────────────────────────────────────

def test_activity_default_params(client):
    with patch(_AUDIT, return_value=[{"event": "x"}]):
        rv = client.get("/api/dashboard/activity")
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["mode"] == "highlight"
    assert data["limit"] == 20
    assert data["count"] == 1


def test_activity_custom_params(client):
    with patch(_AUDIT, return_value=[]):
        rv = client.get("/api/dashboard/activity?mode=verbose&limit=5")
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["mode"] == "verbose"
    assert data["limit"] == 5


def test_activity_invalid_mode_400(client):
    with patch(_AUDIT, return_value=[]):
        rv = client.get("/api/dashboard/activity?mode=invalid")
    assert rv.status_code == 400


# ── GET /api/dashboard/counts ─────────────────────────────────────────────────

def test_counts_best_effort_all_fail_200(client):
    with patch(f"{_SRV}._chroma_client", side_effect=Exception("down")):
        rv = client.get("/api/dashboard/counts")
    assert rv.status_code == 200
    data = rv.get_json()
    for key in ("chars", "scenes", "arcs", "lore_disk"):
        assert key in data


def test_counts_chars_is_dict(client):
    with patch(f"{_SRV}._chroma_client", side_effect=Exception("down")):
        data = client.get("/api/dashboard/counts").get_json()
    assert isinstance(data["chars"], dict)
    assert "db" in data["chars"]
    assert "yaml" in data["chars"]


def test_counts_scenes_is_dict(client):
    with patch(f"{_SRV}._chroma_client", side_effect=Exception("down")):
        data = client.get("/api/dashboard/counts").get_json()
    assert isinstance(data["scenes"], dict)
    assert "db" in data["scenes"]
    assert "disk" in data["scenes"]
