"""Unit test per route HTTP di messages_db_routes.py."""
from __future__ import annotations

import pytest
from flask import Flask

from app.calliope_shell.messages_db_routes import register_messages_db_routes
from app.db import get_db, init_schema, new_id
from app.db.messages import add_message


@pytest.fixture
def seeded(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    scene_id = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "Scene1"))
    conn.commit()
    msg_id = add_message(conn, scene_id=scene_id, author_name="Alice",
                         content_original="Hello", position_order=0)
    conn.commit()
    conn.close()
    return {"path": str(p), "scene_id": scene_id, "msg_id": msg_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config.update(TESTING=True)
    register_messages_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# ── GET /api/db/messages/recent ───────────────────────────────────────────────

def test_recent_messages_200(client):
    c, _ = client
    r = c.get("/api/db/messages/recent")
    assert r.status_code == 200
    assert "messages" in r.get_json()


def test_recent_messages_bad_limit_400(client):
    c, _ = client
    r = c.get("/api/db/messages/recent?limit=0")
    assert r.status_code == 400
    assert r.get_json() == {"error": "bad_request"}


# ── GET /api/db/messages/<message_id> ────────────────────────────────────────

def test_get_message_by_id_200(client):
    c, s = client
    r = c.get(f"/api/db/messages/{s['msg_id']}")
    assert r.status_code == 200


def test_get_message_by_id_404(client):
    c, _ = client
    assert c.get("/api/db/messages/nonexistent").status_code == 404


# ── DELETE /api/db/messages/<message_id> ─────────────────────────────────────

def test_delete_message_204(client):
    c, s = client
    r = c.delete(f"/api/db/messages/{s['msg_id']}")
    assert r.status_code == 204
    assert r.data == b""


def test_delete_message_404(client):
    c, _ = client
    assert c.delete("/api/db/messages/nonexistent").status_code == 404


# ── PATCH /api/db/messages/<message_id> ──────────────────────────────────────

def test_patch_message_200(client):
    c, s = client
    r = c.patch(f"/api/db/messages/{s['msg_id']}", json={"content_original": "Updated"})
    assert r.status_code == 200
    assert r.get_json()["id"] == s["msg_id"]


def test_patch_message_empty_body_400(client):
    c, s = client
    assert c.patch(f"/api/db/messages/{s['msg_id']}", json={}).status_code == 400


def test_patch_message_not_found_404(client):
    c, _ = client
    r = c.patch("/api/db/messages/nonexistent", json={"content_original": "X"})
    assert r.status_code == 404


# ── POST /api/db/scenes/<scene_id>/messages ───────────────────────────────────

def test_append_message_201(client):
    c, s = client
    r = c.post(f"/api/db/scenes/{s['scene_id']}/messages",
               json={"author_name": "Bob", "content_original": "Hi"})
    assert r.status_code == 201
    assert "id" in r.get_json()


def test_append_message_scene_not_found_404(client):
    c, _ = client
    r = c.post("/api/db/scenes/nonexistent/messages",
               json={"author_name": "Bob", "content_original": "Hi"})
    assert r.status_code == 404


def test_append_message_missing_author_400(client):
    c, s = client
    r = c.post(f"/api/db/scenes/{s['scene_id']}/messages",
               json={"content_original": "Hi"})
    assert r.status_code == 400


# ── GET /api/db/scenes/<scene_id>/messages ────────────────────────────────────

def test_get_scene_messages_200(client):
    c, s = client
    r = c.get(f"/api/db/scenes/{s['scene_id']}/messages")
    assert r.status_code == 200
    data = r.get_json()
    assert "messages" in data
    assert "total" in data
    assert "page" in data


# ── GET /api/db/scenes/<scene_id>/messages/count ──────────────────────────────

def test_count_messages_200(client):
    c, s = client
    r = c.get(f"/api/db/scenes/{s['scene_id']}/messages/count")
    assert r.status_code == 200
    data = r.get_json()
    assert data["count"] == 1
    assert data["scene_id"] == s["scene_id"]


# ── PATCH /api/db/messages/<message_id>/position ─────────────────────────────

def test_patch_position_200_success(client):
    c, s = client
    r = c.patch(f"/api/db/messages/{s['msg_id']}/position", json={"position": 0})
    assert r.status_code == 200
    assert r.get_json() == {}


def test_patch_position_400_missing(client):
    c, s = client
    r = c.patch(f"/api/db/messages/{s['msg_id']}/position", json={})
    assert r.status_code == 400


def test_patch_position_400_negative(client):
    c, s = client
    r = c.patch(f"/api/db/messages/{s['msg_id']}/position", json={"position": -1})
    assert r.status_code == 400


def test_patch_position_404_not_found(client):
    c, _ = client
    r = c.patch("/api/db/messages/nonexistent/position", json={"position": 0})
    assert r.status_code == 404


# ── POST /api/db/messages/<message_id>/move ───────────────────────────────────

def test_move_to_scene_200_success(client):
    c, s = client
    r = c.post(
        f"/api/db/messages/{s['msg_id']}/move",
        json={"target_scene_id": s["scene_id"], "position": 0},
    )
    assert r.status_code == 200
    assert r.get_json() == {}


def test_move_to_scene_400_missing_target(client):
    c, s = client
    r = c.post(f"/api/db/messages/{s['msg_id']}/move", json={"position": 0})
    assert r.status_code == 400


def test_move_to_scene_400_missing_position(client):
    c, s = client
    r = c.post(
        f"/api/db/messages/{s['msg_id']}/move",
        json={"target_scene_id": s["scene_id"]},
    )
    assert r.status_code == 400


def test_move_to_scene_404_not_found(client):
    c, s = client
    r = c.post(
        "/api/db/messages/nonexistent/move",
        json={"target_scene_id": s["scene_id"], "position": 0},
    )
    assert r.status_code == 404


# ── POST /api/db/scenes/<scene_id>/messages/insert ───────────────────────────

def test_insert_message_201_success(client):
    c, s = client
    r = c.post(
        f"/api/db/scenes/{s['scene_id']}/messages/insert",
        json={"author_name": "Bob", "content_original": "Hi", "position_order": 0},
    )
    assert r.status_code == 201
    assert "id" in r.get_json()


def test_insert_message_400_missing_field(client):
    c, s = client
    r = c.post(
        f"/api/db/scenes/{s['scene_id']}/messages/insert",
        json={"author_name": "Bob", "position_order": 0},
    )
    assert r.status_code == 400


def test_insert_message_400_negative_position(client):
    c, s = client
    r = c.post(
        f"/api/db/scenes/{s['scene_id']}/messages/insert",
        json={"author_name": "Bob", "content_original": "Hi", "position_order": -1},
    )
    assert r.status_code == 400


def test_insert_message_404_scene_not_found(client):
    c, _ = client
    r = c.post(
        "/api/db/scenes/nonexistent/messages/insert",
        json={"author_name": "Bob", "content_original": "Hi", "position_order": 0},
    )
    assert r.status_code == 404


# ── POST /api/db/scenes/<scene_id>/messages/compact ──────────────────────────

def test_compact_200_success(client):
    c, s = client
    r = c.post(f"/api/db/scenes/{s['scene_id']}/messages/compact")
    assert r.status_code == 200
    assert "count" in r.get_json()


def test_compact_404_scene_not_found(client):
    c, _ = client
    r = c.post("/api/db/scenes/nonexistent/messages/compact")
    assert r.status_code == 404
