"""Regression tests for Sprint B3 — Tono sessione LLM routing toggle.

Q3 operator-decision: routing LLM provider visible + switch button to
Ollama uncensored. POST /api/dashboard/llm_routing flips active profile
between default tier (Cerebras workhorse) and uncensored Ollama.
"""
from __future__ import annotations

import pytest

from app.calliope_shell.server import create_app


@pytest.fixture
def client():
    app, _ = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_routing_get_returns_current_state(client):
    resp = client.get("/api/dashboard/llm_routing")
    assert resp.status_code == 200
    data = resp.get_json()
    for k in ("active_provider", "active_model", "uncensored_active",
              "uncensored_provider", "uncensored_model",
              "default_provider", "default_model"):
        assert k in data, f"missing: {k}"


def test_routing_post_toggle_to_uncensored(client):
    resp = client.post("/api/dashboard/llm_routing",
                        json={"uncensored": True})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["uncensored_active"] is True
    assert data["active_provider"] == "ollama"


def test_routing_post_toggle_back_to_default(client):
    client.post("/api/dashboard/llm_routing", json={"uncensored": True})
    resp = client.post("/api/dashboard/llm_routing",
                        json={"uncensored": False})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["uncensored_active"] is False
    assert data["active_provider"] != "ollama"


def test_routing_post_missing_field_returns_400(client):
    resp = client.post("/api/dashboard/llm_routing", json={})
    assert resp.status_code == 400
    assert "uncensored" in resp.get_json()["error"]


def test_snapshot_reflects_routing_toggle(client):
    client.post("/api/dashboard/llm_routing", json={"uncensored": True})
    data = client.get("/api/dashboard/snapshot").get_json()
    assert data["llm_routing"]["active_provider"] == "ollama"
    assert data["llm_routing"]["uncensored_active"] is True

    client.post("/api/dashboard/llm_routing", json={"uncensored": False})
    data = client.get("/api/dashboard/snapshot").get_json()
    assert data["llm_routing"]["uncensored_active"] is False


def test_template_has_toggle_uncensored_function():
    from pathlib import Path
    tpl = Path(__file__).parents[2] / "app" / "calliope_shell" / "templates" / "shell.html"
    html = tpl.read_text(encoding="utf-8")
    assert "async function _toggleUncensored" in html
    assert "/api/dashboard/llm_routing" in html
    assert "JSON.stringify({uncensored:" in html
