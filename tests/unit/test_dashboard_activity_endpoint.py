"""Regression tests for Sprint C3 — /api/dashboard/activity endpoint.

Reads from audit_trail. Supports mode=highlight|verbose + limit.
"""
from __future__ import annotations

import pytest

from app.calliope_shell import audit_trail, char_memory, plot_arc, server


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    db = tmp_path / "test_activity.db"
    monkeypatch.setattr(char_memory, "_DB_PATH", db)
    monkeypatch.setattr(plot_arc, "DB_PATH", db)
    monkeypatch.setattr(audit_trail, "_DB_PATH", db)
    char_memory.init_db()
    plot_arc.init_db()
    audit_trail.init_db()
    yield db


@pytest.fixture
def client(isolated):
    app, _ = server.create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_activity_endpoint_returns_200_empty(client):
    resp = client.get("/api/dashboard/activity")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["events"] == []
    assert data["mode"] == "highlight"
    assert data["count"] == 0


def test_activity_endpoint_schema(client):
    resp = client.get("/api/dashboard/activity")
    data = resp.get_json()
    for key in ("events", "mode", "limit", "count"):
        assert key in data


def test_activity_endpoint_default_mode_is_highlight(client, isolated):
    audit_trail.log_event("char.create", subject="Aurora")  # highlight
    audit_trail.log_event("char.fact_append", subject="Aurora")  # NOT highlight
    audit_trail.log_event("scene.refine", subject="s1")  # highlight
    data = client.get("/api/dashboard/activity").get_json()
    kinds = {e["kind"] for e in data["events"]}
    assert "char.fact_append" not in kinds
    assert "char.create" in kinds
    assert "scene.refine" in kinds


def test_activity_endpoint_verbose_mode_returns_all_kinds(client, isolated):
    audit_trail.log_event("char.create", subject="A")
    audit_trail.log_event("char.fact_append", subject="A")
    audit_trail.log_event("translate.run", subject="IT_to_EN")
    data = client.get("/api/dashboard/activity?mode=verbose").get_json()
    assert data["count"] == 3
    kinds = {e["kind"] for e in data["events"]}
    assert "char.fact_append" in kinds


def test_activity_endpoint_rejects_invalid_mode(client):
    resp = client.get("/api/dashboard/activity?mode=evil")
    assert resp.status_code == 400


def test_activity_endpoint_respects_limit(client, isolated):
    for i in range(30):
        audit_trail.log_event("char.create", subject=f"char_{i}")
    data = client.get("/api/dashboard/activity?mode=highlight&limit=5").get_json()
    assert data["count"] == 5
    assert data["limit"] == 5


def test_activity_endpoint_clamps_limit_to_100(client, isolated):
    data = client.get("/api/dashboard/activity?limit=9999").get_json()
    assert data["limit"] == 100


def test_activity_endpoint_clamps_limit_to_1_minimum(client, isolated):
    data = client.get("/api/dashboard/activity?limit=0").get_json()
    assert data["limit"] == 1


def test_activity_endpoint_invalid_limit_falls_back_to_default(client, isolated):
    data = client.get("/api/dashboard/activity?limit=notanint").get_json()
    assert data["limit"] == 20


def test_snapshot_endpoint_includes_recent_activity(client, isolated):
    audit_trail.log_event("char.create", subject="Aurora")
    audit_trail.log_event("scene.blend", subject="s1")
    data = client.get("/api/dashboard/snapshot").get_json()
    assert isinstance(data["recent_activity"], list)
    assert len(data["recent_activity"]) == 2
    kinds = {e["kind"] for e in data["recent_activity"]}
    assert "char.create" in kinds
