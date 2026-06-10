"""
Contract test (father-authored acceptance) — WI-20.

Il worker Efesto deve far passare questi test aggiungendo in
`app/calliope_shell/scenes_db_routes.py`:

    POST /api/db/scenes/<scene_id>/messages/insert
    body JSON: {"author_name": str, "content_original": str, "position_order": int}
    -> 201 + {"id": "<uuid>"}
    -> 400 se manca author_name o content_original o position_order
    -> 404 se scene_id non esiste

Usa SOLO: db_messages.insert_message_at(conn, *, scene_id, author_name,
          content_original, position_order) -> str
  app/db/messages.py:85 — keyword-only, ritorna id messaggio.

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
                content_original="primo", position_order=0)
    add_message(conn, scene_id=scene_id, author_name="Bob",
                content_original="terzo", position_order=1)
    conn.close()
    return {"path": str(p), "scene_id": scene_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# --- WI-20: insert message at position --------------------------------------

def test_insert_at_returns_201_with_id(client):
    c, s = client
    r = c.post(f"/api/db/scenes/{s['scene_id']}/messages/insert",
               json={"author_name": "Carol", "content_original": "secondo",
                     "position_order": 1})
    assert r.status_code == 201
    body = r.get_json()
    assert "id" in body and len(body["id"]) > 0


def test_insert_at_shifts_later_messages(client):
    c, s = client
    c.post(f"/api/db/scenes/{s['scene_id']}/messages/insert",
           json={"author_name": "Carol", "content_original": "secondo",
                 "position_order": 1})
    msgs = c.get(f"/api/db/scenes/{s['scene_id']}").get_json()["messages"]
    assert len(msgs) == 3
    contents = [m["content_original"] for m in msgs]
    assert contents.index("secondo") < contents.index("terzo")


def test_insert_at_scene_not_found_404(client):
    c, _ = client
    r = c.post("/api/db/scenes/scena-inesistente/messages/insert",
               json={"author_name": "X", "content_original": "Y",
                     "position_order": 0})
    assert r.status_code == 404


def test_insert_at_missing_fields_400(client):
    c, s = client
    r = c.post(f"/api/db/scenes/{s['scene_id']}/messages/insert",
               json={"author_name": "X"})  # mancano content_original e position_order
    assert r.status_code == 400
