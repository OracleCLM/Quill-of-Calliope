"""
Contract test (father-authored acceptance) — WI-11.

Il worker Efesto deve far passare questi test aggiungendo in
`app/calliope_shell/scenes_db_routes.py`:

    DELETE /api/db/messages/<message_id>
    - 204 se il messaggio esiste ed è stato eliminato
    - 404 se message_id non esiste nel DB

Usa SOLO: app.db.messages.delete_message(conn, message_id) -> bool
(già implementata, ritorna True se eliminato, False se non esisteva)

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema, new_id
from app.db.messages import add_message
from app.calliope_shell.scenes_db_routes import register_scenes_db_routes


@pytest.fixture
def seeded(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    scene_id = new_id()
    char_id = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "S"))
    conn.execute("INSERT INTO characters (id, name) VALUES (?, ?)", (char_id, "A"))
    conn.commit()
    add_message(conn, scene_id=scene_id, author_name="Alice",
                content_original="first", position_order=0)
    add_message(conn, scene_id=scene_id, author_name="Bob",
                content_original="second", position_order=1)
    conn.close()
    return {"path": str(p), "scene_id": scene_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


def _first_message_id(c, scene_id):
    return c.get(f"/api/db/scenes/{scene_id}").get_json()["messages"][0]["id"]


# --- WI-11: delete message ---------------------------------------------------

def test_delete_message_returns_204(client):
    c, s = client
    mid = _first_message_id(c, s["scene_id"])
    r = c.delete(f"/api/db/messages/{mid}")
    assert r.status_code == 204


def test_delete_message_removes_from_scene(client):
    c, s = client
    mid = _first_message_id(c, s["scene_id"])
    c.delete(f"/api/db/messages/{mid}")
    detail = c.get(f"/api/db/scenes/{s['scene_id']}").get_json()
    ids = [m["id"] for m in detail["messages"]]
    assert mid not in ids
    assert len(ids) == 1  # era 2, ora 1


def test_delete_message_not_found_404(client):
    c, _ = client
    r = c.delete("/api/db/messages/id-che-non-esiste")
    assert r.status_code == 404


def test_delete_message_idempotent_second_call_404(client):
    c, s = client
    mid = _first_message_id(c, s["scene_id"])
    c.delete(f"/api/db/messages/{mid}")
    r = c.delete(f"/api/db/messages/{mid}")
    assert r.status_code == 404
