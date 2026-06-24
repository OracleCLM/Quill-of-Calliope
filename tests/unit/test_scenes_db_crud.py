"""Unit test per CRUD route non coperte di scenes_db_routes (POST/PATCH/DELETE/merge/duplicate)."""
from __future__ import annotations

import pytest
from flask import Flask

from app.calliope_shell.scenes_db_routes import register_scenes_db_routes
from app.db import get_db, init_schema, new_id


@pytest.fixture
def seeded(tmp_path):
    p = tmp_path / "calliope_test.db"
    conn = get_db(p)
    init_schema(conn)
    scene_id_a = new_id()
    scene_id_b = new_id()
    conn.execute("INSERT INTO scenes (id, title, location) VALUES (?, ?, ?)", (scene_id_a, "Test Scene A", "Forest"))
    conn.execute("INSERT INTO scenes (id, title, location) VALUES (?, ?, ?)", (scene_id_b, "Test Scene B", "City"))
    conn.commit()
    conn.close()
    return {"path": str(p), "scene_id": scene_id_a, "scene_id_b": scene_id_b}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config.update(TESTING=True)
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# ── POST /api/db/scenes ───────────────────────────────────────────────────────

def test_create_scene_title_only_201(client):
    c, _ = client
    r = c.post("/api/db/scenes", json={"title": "X"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["title"] == "X"
    assert data["location"] is None
    assert "id" in data


def test_create_scene_with_location_201(client):
    c, _ = client
    r = c.post("/api/db/scenes", json={"title": "X", "location": "Forest"})
    assert r.status_code == 201
    assert r.get_json()["location"] == "Forest"


def test_create_scene_missing_title_400(client):
    c, _ = client
    r = c.post("/api/db/scenes", json={})
    assert r.status_code == 400
    assert r.get_json()["error"] == "title required"


def test_create_scene_empty_title_400(client):
    c, _ = client
    r = c.post("/api/db/scenes", json={"title": ""})
    assert r.status_code == 400
    assert r.get_json()["error"] == "title required"


# ── PATCH /api/db/scenes/<scene_id> ──────────────────────────────────────────

def test_patch_scene_title_200(client):
    c, s = client
    r = c.patch(f"/api/db/scenes/{s['scene_id']}", json={"title": "Y"})
    assert r.status_code == 200


def test_patch_scene_no_fields_400(client):
    c, s = client
    r = c.patch(f"/api/db/scenes/{s['scene_id']}", json={})
    assert r.status_code == 400
    assert r.get_json()["error"] == "no updatable fields"


def test_patch_scene_empty_title_400(client):
    c, s = client
    r = c.patch(f"/api/db/scenes/{s['scene_id']}", json={"title": ""})
    assert r.status_code == 400
    assert r.get_json()["error"] == "title cannot be empty"


def test_patch_scene_not_found_404(client):
    c, _ = client
    r = c.patch(f"/api/db/scenes/{new_id()}", json={"title": "Z"})
    assert r.status_code == 404


# ── DELETE /api/db/scenes/<scene_id> ─────────────────────────────────────────

def test_delete_scene_204(client):
    c, s = client
    r = c.delete(f"/api/db/scenes/{s['scene_id']}")
    assert r.status_code == 204
    assert r.data == b""


def test_delete_scene_not_found_404(client):
    c, _ = client
    r = c.delete(f"/api/db/scenes/{new_id()}")
    assert r.status_code == 404
    assert r.get_json()["error"] == "not_found"


# ── POST /api/db/scenes/merge ─────────────────────────────────────────────────

def test_merge_scenes_201(client):
    c, s = client
    r = c.post("/api/db/scenes/merge", json={
        "scene_id_a": s["scene_id"],
        "scene_id_b": s["scene_id_b"],
        "new_name": "Merged",
    })
    assert r.status_code == 201
    assert "merged_scene_id" in r.get_json()


def test_merge_scenes_missing_fields_400(client):
    c, _ = client
    r = c.post("/api/db/scenes/merge", json={})
    assert r.status_code == 400
    assert r.get_json()["error"] == "bad_request"


def test_merge_scenes_self_merge_400(client):
    c, s = client
    r = c.post("/api/db/scenes/merge", json={
        "scene_id_a": s["scene_id"],
        "scene_id_b": s["scene_id"],
        "new_name": "M",
    })
    assert r.status_code == 400


# ── POST /api/db/scenes/<scene_id>/duplicate ─────────────────────────────────

def test_duplicate_scene_201(client):
    c, s = client
    r = c.post(f"/api/db/scenes/{s['scene_id']}/duplicate", json={"new_name": "Copy"})
    assert r.status_code == 201
    assert "new_scene_id" in r.get_json()


def test_duplicate_scene_missing_name_400(client):
    c, s = client
    r = c.post(f"/api/db/scenes/{s['scene_id']}/duplicate", json={})
    assert r.status_code == 400
