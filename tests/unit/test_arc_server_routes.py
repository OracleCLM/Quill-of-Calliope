"""GAP-76: test per route /api/arc in server.py (legacy plot_arc)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from app.calliope_shell.server import create_app


@pytest.fixture
def client():
    app, _ = create_app()
    app.config["TESTING"] = True
    return app.test_client()


# ── GET /api/arc ──────────────────────────────────────────────────────────────


def test_arc_list_returns_200(client):
    r = client.get("/api/arc")
    assert r.status_code == 200


def test_arc_list_returns_list(client):
    data = client.get("/api/arc").get_json()
    assert isinstance(data, list)


# ── POST /api/arc ─────────────────────────────────────────────────────────────


def test_arc_create_missing_arc_id_returns_400(client):
    r = client.post("/api/arc", json={"title": "Test"})
    assert r.status_code == 400


def test_arc_create_missing_title_returns_400(client):
    r = client.post("/api/arc", json={"arc_id": "test-arc"})
    assert r.status_code == 400


def test_arc_create_returns_201(client):
    r = client.post("/api/arc", json={"arc_id": "new-arc-01", "title": "Arc Uno", "chars": []})
    assert r.status_code == 201


def test_arc_create_response_has_arc_id(client):
    r = client.post("/api/arc", json={"arc_id": "new-arc-02", "title": "Arc Due"})
    data = r.get_json()
    assert "arc_id" in data


# ── GET /api/arc/<arc_id> ─────────────────────────────────────────────────────


def test_arc_get_not_found_returns_404(client):
    r = client.get("/api/arc/arc-inesistente-xyz")
    assert r.status_code == 404


def test_arc_get_existing_returns_200(client):
    client.post("/api/arc", json={"arc_id": "arc-test-get", "title": "Test Get"})
    r = client.get("/api/arc/arc-test-get")
    assert r.status_code == 200


# ── POST /api/arc/search ──────────────────────────────────────────────────────


def test_arc_search_missing_query_returns_400(client):
    r = client.post("/api/arc/search", json={})
    assert r.status_code == 400


def test_arc_search_returns_results_list(client):
    r = client.post("/api/arc/search", json={"query": "dragon"})
    assert r.status_code == 200
    data = r.get_json()
    assert "results" in data


# ── GET /api/arc/<arc_id>/threads ─────────────────────────────────────────────


def test_arc_threads_returns_200(client):
    client.post("/api/arc", json={"arc_id": "arc-threads", "title": "Threads Test"})
    r = client.get("/api/arc/arc-threads/threads")
    assert r.status_code == 200


def test_arc_threads_has_threads_key(client):
    client.post("/api/arc", json={"arc_id": "arc-threads2", "title": "Threads2"})
    data = client.get("/api/arc/arc-threads2/threads").get_json()
    assert "threads" in data
