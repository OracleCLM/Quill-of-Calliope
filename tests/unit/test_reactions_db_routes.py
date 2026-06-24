"""
Test per app/calliope_shell/reactions_db_routes.py.

Endpoint coperti:
  GET  /api/db/messages/<id>/reactions → 200 lista
  POST /api/db/messages/<id>/reactions → 201 | 400 | 404
  DELETE /api/db/messages/<id>/reactions/<rid> → 204 | 404
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from flask import Flask

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.reactions_db_routes import register_reactions_db_routes
from app.db import get_db, init_schema
from app.db.characters import add_character, add_character_to_scene
from app.db.messages import add_message


@pytest.fixture
def client(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(str(p))
    init_schema(conn)
    conn.close()
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_reactions_db_routes(app, db_path=str(p))
    return app.test_client(), str(p)


def _setup(db_path: str):
    """Crea scena + personaggio + messaggio; ritorna (char_id, message_id)."""
    from app.db import new_id
    conn = get_db(db_path)
    scene_id = new_id()
    conn.execute(
        "INSERT INTO scenes(id,title,created_at,updated_at) VALUES(?,?,datetime('now'),datetime('now'))",
        (scene_id, "Scena R"),
    )
    conn.commit()
    char_id = add_character(conn, name="Aurora")
    add_character_to_scene(conn, scene_id, char_id)
    message_id = add_message(conn, scene_id=scene_id, author_name="Aurora",
                             content_original="Ciao")
    conn.close()
    return char_id, message_id


# ── GET reactions ─────────────────────────────────────────────────────────────

def test_get_reactions_empty(client):
    c, _ = client
    r = c.get("/api/db/messages/nonexistent/reactions")
    assert r.status_code == 200
    assert r.get_json()["reactions"] == []


def test_get_reactions_after_add(client):
    c, db_path = client
    char_id, message_id = _setup(db_path)
    c.post(f"/api/db/messages/{message_id}/reactions",
           json={"character_id": char_id, "emoji": "❤️"})
    r = c.get(f"/api/db/messages/{message_id}/reactions")
    assert r.status_code == 200
    assert len(r.get_json()["reactions"]) == 1


# ── POST reactions ────────────────────────────────────────────────────────────

def test_post_reaction_created(client):
    c, db_path = client
    char_id, message_id = _setup(db_path)
    r = c.post(f"/api/db/messages/{message_id}/reactions",
               json={"character_id": char_id, "emoji": "🔥"})
    assert r.status_code == 201
    assert "id" in r.get_json()


def test_post_reaction_missing_character_id_400(client):
    c, db_path = client
    _, message_id = _setup(db_path)
    r = c.post(f"/api/db/messages/{message_id}/reactions", json={"emoji": "❤️"})
    assert r.status_code == 400


def test_post_reaction_message_not_found_404(client):
    c, db_path = client
    char_id, _ = _setup(db_path)
    r = c.post("/api/db/messages/ghost-msg/reactions",
               json={"character_id": char_id, "emoji": "❤️"})
    assert r.status_code == 404


def test_post_reaction_default_emoji(client):
    c, db_path = client
    char_id, message_id = _setup(db_path)
    r = c.post(f"/api/db/messages/{message_id}/reactions",
               json={"character_id": char_id})
    assert r.status_code == 201


# ── DELETE reaction ───────────────────────────────────────────────────────────

def test_delete_reaction_204(client):
    c, db_path = client
    char_id, message_id = _setup(db_path)
    post_r = c.post(f"/api/db/messages/{message_id}/reactions",
                    json={"character_id": char_id, "emoji": "🔥"})
    reaction_id = post_r.get_json()["id"]
    del_r = c.delete(f"/api/db/messages/{message_id}/reactions/{reaction_id}")
    assert del_r.status_code == 204


def test_delete_reaction_not_found_404(client):
    c, _ = client
    r = c.delete("/api/db/messages/msg/reactions/ghost-rid")
    assert r.status_code == 404
