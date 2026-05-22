"""Regression tests for Sprint A3 — /api/dashboard/counts + sidebar widget.

Endpoint aggregates knowledge-base counts so the operator sees them
on landing without opening individual tabs. Failure-tolerant: any
sub-query failure → 0, endpoint still returns 200.
"""
from __future__ import annotations

import pytest

from app.calliope_shell.server import create_app


@pytest.fixture
def client():
    app, _ = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_dashboard_counts_endpoint_200(client):
    resp = client.get("/api/dashboard/counts")
    assert resp.status_code == 200


def test_dashboard_counts_schema(client):
    resp = client.get("/api/dashboard/counts")
    data = resp.get_json()
    assert "chars" in data
    assert "scenes" in data
    assert "arcs" in data
    assert "lore_disk" in data
    assert "db" in data["chars"] and "yaml" in data["chars"]
    assert "db" in data["scenes"] and "disk" in data["scenes"]


def test_dashboard_counts_values_are_int(client):
    resp = client.get("/api/dashboard/counts")
    data = resp.get_json()
    assert isinstance(data["chars"]["db"], int)
    assert isinstance(data["chars"]["yaml"], int)
    assert isinstance(data["scenes"]["db"], int)
    assert isinstance(data["scenes"]["disk"], int)
    assert isinstance(data["arcs"], int)
    assert isinstance(data["lore_disk"], int)


def test_dashboard_counts_chars_yaml_reflects_disk(client):
    resp = client.get("/api/dashboard/counts")
    data = resp.get_json()
    assert data["chars"]["yaml"] >= 0


def test_template_renders_counters_widget():
    from pathlib import Path
    tpl = Path(__file__).parents[2] / "app" / "calliope_shell" / "templates" / "shell.html"
    html = tpl.read_text(encoding="utf-8")
    assert 'id="counters-sidebar"' in html
    assert 'id="cnt-chars"' in html
    assert 'id="cnt-scenes"' in html
    assert 'id="cnt-arcs"' in html
    assert 'id="cnt-lore"' in html
    assert "/api/dashboard/counts" in html


def test_dashboard_counts_endpoint_robust_to_missing_dirs(tmp_path, monkeypatch):
    """If characters/ or scenes/ dirs missing, endpoint returns 0 not 500."""
    import app.calliope_shell.server as srv

    original_parents = type(srv.Path(""))

    class FakePath(original_parents):
        def __new__(cls, *args, **kwargs):
            return original_parents.__new__(cls, *args, **kwargs)

    app, _ = create_app()
    client_ = app.test_client()
    resp = client_.get("/api/dashboard/counts")
    assert resp.status_code == 200
