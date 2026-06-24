"""
Test per app/calliope_shell/scene_characters_db_routes.py.

Endpoint coperti:
  GET    /api/db/scenes/<id>/characters → 200 | 404
  POST   /api/db/scenes/<id>/characters → 201 | 400 | 404 | 409
  PATCH  /api/db/scenes/<id>/characters/<cid> → 200 | 400 | 404
  DELETE /api/db/scenes/<id>/characters/<cid> → 204 | 404
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from flask import Flask

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.scene_characters_db_routes import (
    register_scene_characters_db_routes,
)
from app.db import get_db, init_schema
from app.db.characters import add_character
from tests.unit.conftest import add_scene


@pytest.fixture
def client(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(str(p))
    init_schema(conn)
    conn.close()
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scene_characters_db_routes(app, db_path=str(p))
    return app.test_client(), str(p)


def _make_scene(db_path: str, title: str = "Scena SC") -> str:
    conn = get_db(db_path)
    scene_id = add_scene(conn, title=title)
    conn.close()
    return scene_id


def _make_char(db_path: str, name: str = "Aurora") -> str:
    conn = get_db(db_path)
    char_id = add_character(conn, name=name)
    conn.close()
    return char_id


# ── GET /api/db/scenes/<id>/characters ───────────────────────────────────────

def test_get_scene_chars_scene_not_found(client):
    c, _ = client
    r = c.get("/api/db/scenes/ghost/characters")
    assert r.status_code == 404


def test_get_scene_chars_empty(client):
    c, db_path = client
    scene_id = _make_scene(db_path)
    r = c.get(f"/api/db/scenes/{scene_id}/characters")
    assert r.status_code == 200
    assert r.get_json()["characters"] == []


def test_get_scene_chars_after_add(client):
    c, db_path = client
    scene_id = _make_scene(db_path)
    char_id = _make_char(db_path)
    c.post(f"/api/db/scenes/{scene_id}/characters",
           json={"character_id": char_id})
    r = c.get(f"/api/db/scenes/{scene_id}/characters")
    assert r.status_code == 200
    assert len(r.get_json()["characters"]) == 1


# ── POST /api/db/scenes/<id>/characters ──────────────────────────────────────

def test_post_add_char_to_scene_201(client):
    c, db_path = client
    scene_id = _make_scene(db_path)
    char_id = _make_char(db_path)
    r = c.post(f"/api/db/scenes/{scene_id}/characters",
               json={"character_id": char_id, "role": "protagonist"})
    assert r.status_code == 201


def test_post_add_char_scene_not_found_404(client):
    c, db_path = client
    char_id = _make_char(db_path)
    r = c.post("/api/db/scenes/ghost/characters",
               json={"character_id": char_id})
    assert r.status_code == 404


def test_post_add_char_missing_character_id_400(client):
    c, db_path = client
    scene_id = _make_scene(db_path)
    r = c.post(f"/api/db/scenes/{scene_id}/characters", json={})
    assert r.status_code == 400


def test_post_add_char_char_not_found_404(client):
    c, db_path = client
    scene_id = _make_scene(db_path)
    r = c.post(f"/api/db/scenes/{scene_id}/characters",
               json={"character_id": "ghost-char"})
    assert r.status_code == 404


def test_post_add_char_duplicate_409(client):
    c, db_path = client
    scene_id = _make_scene(db_path)
    char_id = _make_char(db_path)
    c.post(f"/api/db/scenes/{scene_id}/characters",
           json={"character_id": char_id})
    r = c.post(f"/api/db/scenes/{scene_id}/characters",
               json={"character_id": char_id})
    assert r.status_code == 409


def test_post_add_char_default_role_participant(client):
    c, db_path = client
    scene_id = _make_scene(db_path)
    char_id = _make_char(db_path)
    c.post(f"/api/db/scenes/{scene_id}/characters",
           json={"character_id": char_id})
    r = c.get(f"/api/db/scenes/{scene_id}/characters")
    chars = r.get_json()["characters"]
    assert chars[0]["role"] == "participant"


# ── PATCH /api/db/scenes/<id>/characters/<cid> ───────────────────────────────

def test_patch_role_200(client):
    c, db_path = client
    scene_id = _make_scene(db_path)
    char_id = _make_char(db_path)
    c.post(f"/api/db/scenes/{scene_id}/characters",
           json={"character_id": char_id})
    r = c.patch(f"/api/db/scenes/{scene_id}/characters/{char_id}",
                json={"role": "antagonist"})
    assert r.status_code == 200


def test_patch_role_missing_400(client):
    c, db_path = client
    scene_id = _make_scene(db_path)
    char_id = _make_char(db_path)
    r = c.patch(f"/api/db/scenes/{scene_id}/characters/{char_id}", json={})
    assert r.status_code == 400


def test_patch_role_not_found_404(client):
    c, _ = client
    r = c.patch("/api/db/scenes/ghost/characters/ghost",
                json={"role": "protagonist"})
    assert r.status_code == 404


# ── DELETE /api/db/scenes/<id>/characters/<cid> ──────────────────────────────

def test_delete_char_from_scene_204(client):
    c, db_path = client
    scene_id = _make_scene(db_path)
    char_id = _make_char(db_path)
    c.post(f"/api/db/scenes/{scene_id}/characters",
           json={"character_id": char_id})
    r = c.delete(f"/api/db/scenes/{scene_id}/characters/{char_id}")
    assert r.status_code == 204


def test_delete_char_from_scene_not_found_404(client):
    c, db_path = client
    scene_id = _make_scene(db_path)
    char_id = _make_char(db_path)
    r = c.delete(f"/api/db/scenes/{scene_id}/characters/{char_id}")
    assert r.status_code == 404
