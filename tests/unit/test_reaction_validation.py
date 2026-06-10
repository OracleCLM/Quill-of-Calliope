"""
Contract test (father-authored acceptance) — WI-29.

Il worker Efesto deve far passare questi test modificando in
`app/calliope_shell/scenes_db_routes.py` la route POST /api/db/messages/<id>/reactions:

    POST /api/db/messages/<message_id>/reactions
    body JSON mancante di character_id -> 400
    message_id inesistente -> 404  (verificare che il messaggio esiste prima di inserire)

La route DEVE:
1. Validare che character_id sia presente nel body (400 se assente)
2. Verificare che message_id esista in DB prima di chiamare add_reaction (404 se non esiste)
   Usa: db_messages.get_message_by_id(conn, message_id) e' None -> 404

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
                content_original="ciao", position_order=0)
    conn.close()
    return {"path": str(p), "scene_id": scene_id, "char_id": char_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


def _first_msg_id(c, scene_id):
    return c.get(f"/api/db/scenes/{scene_id}").get_json()["messages"][0]["id"]


# --- WI-29: reaction validation ----------------------------------------------

def test_reaction_missing_character_id_400(client):
    c, s = client
    mid = _first_msg_id(c, s["scene_id"])
    r = c.post(f"/api/db/messages/{mid}/reactions",
               json={"emoji": "fire"})  # manca character_id
    assert r.status_code == 400


def test_reaction_nonexistent_message_404(client):
    c, s = client
    r = c.post("/api/db/messages/msg-inesistente/reactions",
               json={"character_id": s["char_id"], "emoji": "fire"})
    assert r.status_code == 404


def test_reaction_valid_returns_201(client):
    c, s = client
    mid = _first_msg_id(c, s["scene_id"])
    r = c.post(f"/api/db/messages/{mid}/reactions",
               json={"character_id": s["char_id"], "emoji": "fire"})
    assert r.status_code == 201
