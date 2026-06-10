"""
Contract test (father-authored acceptance) — WI-22.

Il worker Efesto deve far passare questi test aggiungendo in
`app/calliope_shell/scenes_db_routes.py`:

    POST /api/db/messages/<message_id>/move
    body JSON: {"target_scene_id": str, "position": int}
    -> 200 se spostato
    -> 400 se manca target_scene_id o position
    -> 404 se message_id non esiste

Usa SOLO: db_messages.move_message_to_scene(conn, message_id, target_scene_id, new_position) -> bool
  app/db/messages.py:441 — ritorna False se il messaggio non esiste.

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
    src_id = new_id()
    dst_id = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (src_id, "Sorgente"))
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (dst_id, "Destinazione"))
    conn.commit()
    add_message(conn, scene_id=src_id, author_name="Alice",
                content_original="da spostare", position_order=0)
    add_message(conn, scene_id=src_id, author_name="Bob",
                content_original="rimane", position_order=1)
    conn.close()
    return {"path": str(p), "src_id": src_id, "dst_id": dst_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


def _first_msg_id(c, scene_id):
    return c.get(f"/api/db/scenes/{scene_id}").get_json()["messages"][0]["id"]


# --- WI-22: move message to another scene -----------------------------------

def test_move_to_scene_returns_200(client):
    c, s = client
    mid = _first_msg_id(c, s["src_id"])
    r = c.post(f"/api/db/messages/{mid}/move",
               json={"target_scene_id": s["dst_id"], "position": 0})
    assert r.status_code == 200


def test_move_to_scene_message_in_destination(client):
    c, s = client
    mid = _first_msg_id(c, s["src_id"])
    c.post(f"/api/db/messages/{mid}/move",
           json={"target_scene_id": s["dst_id"], "position": 0})
    dst_msgs = c.get(f"/api/db/scenes/{s['dst_id']}").get_json()["messages"]
    dst_ids = [m["id"] for m in dst_msgs]
    assert mid in dst_ids


def test_move_to_scene_removed_from_source(client):
    c, s = client
    mid = _first_msg_id(c, s["src_id"])
    c.post(f"/api/db/messages/{mid}/move",
           json={"target_scene_id": s["dst_id"], "position": 0})
    src_msgs = c.get(f"/api/db/scenes/{s['src_id']}").get_json()["messages"]
    src_ids = [m["id"] for m in src_msgs]
    assert mid not in src_ids
    assert len(src_msgs) == 1  # era 2, ora 1


def test_move_to_scene_message_not_found_404(client):
    c, s = client
    r = c.post("/api/db/messages/msg-inesistente/move",
               json={"target_scene_id": s["dst_id"], "position": 0})
    assert r.status_code == 404


def test_move_to_scene_missing_body_400(client):
    c, s = client
    mid = _first_msg_id(c, s["src_id"])
    r = c.post(f"/api/db/messages/{mid}/move", json={})
    assert r.status_code == 400
