"""
Contract test (father-authored acceptance) — WI-14.

Il worker Efesto deve far passare questi test aggiungendo in
`app/calliope_shell/scenes_db_routes.py`:

    GET /api/db/messages/<message_id>
    - 200 + dizionario messaggio (id, scene_id, author_name, content_original, ...)
    - 404 se message_id non esiste

Usa SOLO: db_messages.get_message_by_id(conn, message_id)
  gia' in app/db/messages.py:216, importata come db_messages in scenes_db_routes.

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
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "S"))
    conn.commit()
    add_message(conn, scene_id=scene_id, author_name="Alice",
                content_original="ciao", position_order=0)
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


# --- WI-14: GET /api/db/messages/<id> ----------------------------------------

def test_get_message_by_id_200(client):
    c, s = client
    mid = _first_message_id(c, s["scene_id"])
    r = c.get(f"/api/db/messages/{mid}")
    assert r.status_code == 200


def test_get_message_by_id_response_shape(client):
    c, s = client
    mid = _first_message_id(c, s["scene_id"])
    data = c.get(f"/api/db/messages/{mid}").get_json()
    assert data["id"] == mid
    assert data["scene_id"] == s["scene_id"]
    assert data["author_name"] == "Alice"
    assert data["content_original"] == "ciao"


def test_get_message_by_id_not_found_404(client):
    c, _ = client
    r = c.get("/api/db/messages/id-inesistente-xyz")
    assert r.status_code == 404
