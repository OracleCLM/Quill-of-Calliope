"""Unit test per route CRUD /api/db/arcs di arcs_db_routes.py."""
from __future__ import annotations

import pytest
from flask import Flask

from app.calliope_shell.arcs_db_routes import register_arcs_db_routes
from app.db import get_db, init_schema


@pytest.fixture
def seeded(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    conn.commit()
    conn.close()
    return str(p)


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config.update(TESTING=True)
    register_arcs_db_routes(app, db_path=seeded)
    return app.test_client()


# ── POST /api/db/arcs ────────────────────────────────────────────────────────

def test_create_arc_201(client):
    r = client.post("/api/db/arcs", json={"title": "T"})
    assert r.status_code == 201
    data = r.get_json()
    assert "id" in data
    assert data["title"] == "T"


def test_create_arc_missing_title_400(client):
    r = client.post("/api/db/arcs", json={})
    assert r.status_code == 400
    assert r.get_json() == {"error": "title required"}


def test_create_arc_with_description_201(client):
    r = client.post("/api/db/arcs", json={"title": "T", "description": "D"})
    assert r.status_code == 201
    assert r.get_json()["title"] == "T"


# ── GET /api/db/arcs ─────────────────────────────────────────────────────────

def test_list_arcs_empty(client):
    r = client.get("/api/db/arcs")
    assert r.status_code == 200
    assert r.get_json()["arcs"] == []


def test_list_arcs_returns_created(client):
    client.post("/api/db/arcs", json={"title": "Arc1"})
    data = client.get("/api/db/arcs").get_json()
    assert len(data["arcs"]) == 1
    assert data["arcs"][0]["title"] == "Arc1"


# ── GET /api/db/arcs/<arc_id> ────────────────────────────────────────────────

def test_get_arc_200(client):
    arc_id = client.post("/api/db/arcs", json={"title": "Arc1"}).get_json()["id"]
    data = client.get(f"/api/db/arcs/{arc_id}").get_json()
    assert data["id"] == arc_id
    assert data["title"] == "Arc1"


def test_get_arc_not_found_404(client):
    r = client.get("/api/db/arcs/nonexistent")
    assert r.status_code == 404
    assert r.get_json() == {"error": "not_found"}


# ── DELETE /api/db/arcs/<arc_id> ─────────────────────────────────────────────

def test_delete_arc_204(client):
    arc_id = client.post("/api/db/arcs", json={"title": "Arc1"}).get_json()["id"]
    r = client.delete(f"/api/db/arcs/{arc_id}")
    assert r.status_code == 204
    assert r.data == b""


def test_delete_arc_not_found_404(client):
    assert client.delete("/api/db/arcs/nonexistent").status_code == 404


# ── GET /api/db/arcs/<arc_id>/scenes ─────────────────────────────────────────

def test_arc_scenes_empty_list(client):
    arc_id = client.post("/api/db/arcs", json={"title": "Arc1"}).get_json()["id"]
    data = client.get(f"/api/db/arcs/{arc_id}/scenes").get_json()
    assert data["scenes"] == []
    assert data["arc_id"] == arc_id


def test_arc_scenes_not_found_404(client):
    assert client.get("/api/db/arcs/nonexistent/scenes").status_code == 404


# ── PATCH /api/db/arcs/<arc_id> ──────────────────────────────────────────────

def test_patch_arc_200(client):
    arc_id = client.post("/api/db/arcs", json={"title": "Old"}).get_json()["id"]
    r = client.patch(f"/api/db/arcs/{arc_id}", json={"title": "New"})
    assert r.status_code == 200
    assert r.get_json()["title"] == "New"


def test_patch_arc_no_fields_400(client):
    arc_id = client.post("/api/db/arcs", json={"title": "T"}).get_json()["id"]
    r = client.patch(f"/api/db/arcs/{arc_id}", json={})
    assert r.status_code == 400
    assert r.get_json() == {"error": "no updatable fields"}
