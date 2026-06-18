"""GAP-83: test per /api/db/messages/<id>/reactions (GET/POST/DELETE)."""

import sys
from pathlib import Path

import pytest
from flask import Flask

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.reactions_db_routes import register_reactions_db_routes
from app.db import get_db, init_schema, new_id
from app.db.messages import add_message


@pytest.fixture
def client(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    conn.close()
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_reactions_db_routes(app, db_path=str(p))
    return app.test_client(), str(p)


def _setup(db_path):
    conn = get_db(db_path)
    scene_id = new_id()
    char_id = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "S"))
    conn.execute("INSERT INTO characters (id, name) VALUES (?, ?)", (char_id, "Char"))
    conn.commit()
    msg_id = add_message(conn, scene_id=scene_id, author_name="Char",
                         content_original="ciao", position_order=0)
    conn.commit()
    conn.close()
    return msg_id, char_id


# ── GET /api/db/messages/<id>/reactions ──────────────────────────────────────


def test_list_reactions_returns_200(client):
    c, db = client
    msg_id, _ = _setup(db)
    r = c.get(f"/api/db/messages/{msg_id}/reactions")
    assert r.status_code == 200


def test_list_reactions_empty_on_new_message(client):
    c, db = client
    msg_id, _ = _setup(db)
    data = c.get(f"/api/db/messages/{msg_id}/reactions").get_json()
    assert "reactions" in data
    assert data["reactions"] == []


# ── POST /api/db/messages/<id>/reactions ─────────────────────────────────────


def test_add_reaction_missing_char_id_returns_400(client):
    c, db = client
    msg_id, _ = _setup(db)
    r = c.post(f"/api/db/messages/{msg_id}/reactions", json={"emoji": "❤️"})
    assert r.status_code == 400


def test_add_reaction_message_not_found_returns_404(client):
    c, db = client
    r = c.post("/api/db/messages/nonexistent/reactions", json={"character_id": "x"})
    assert r.status_code == 404


def test_add_reaction_ok_returns_201(client):
    c, db = client
    msg_id, char_id = _setup(db)
    r = c.post(f"/api/db/messages/{msg_id}/reactions",
               json={"character_id": char_id, "emoji": "👍"})
    assert r.status_code == 201
    assert "id" in r.get_json()


def test_add_reaction_appears_in_list(client):
    c, db = client
    msg_id, char_id = _setup(db)
    c.post(f"/api/db/messages/{msg_id}/reactions",
           json={"character_id": char_id, "emoji": "👍"})
    data = c.get(f"/api/db/messages/{msg_id}/reactions").get_json()
    assert len(data["reactions"]) == 1


# ── DELETE /api/db/messages/<id>/reactions/<reaction_id> ─────────────────────


def test_delete_reaction_returns_204(client):
    c, db = client
    msg_id, char_id = _setup(db)
    reaction_id = c.post(f"/api/db/messages/{msg_id}/reactions",
                         json={"character_id": char_id, "emoji": "❤️"}).get_json()["id"]
    r = c.delete(f"/api/db/messages/{msg_id}/reactions/{reaction_id}")
    assert r.status_code == 204


def test_delete_reaction_not_found_returns_404(client):
    c, db = client
    msg_id, _ = _setup(db)
    r = c.delete(f"/api/db/messages/{msg_id}/reactions/nonexistent-id")
    assert r.status_code == 404
