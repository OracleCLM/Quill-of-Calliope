"""
Contract test (father-authored acceptance) — WI-40.

Il worker Efesto deve far passare questi test aggiungendo:

1. In `app/db/messages.py` la funzione:
       update_message(
           conn: sqlite3.Connection,
           message_id: str,
           *,
           content_original: str | None = None,
           author_name: str | None = None,
       ) -> bool
       - aggiorna solo i campi non-None
       - ritorna True se aggiornato, False se message_id non esiste
       - raise ValueError se nessun campo e' fornito (entrambi None)

2. Route in `app/calliope_shell/scenes_db_routes.py`:
       PATCH /api/db/messages/<message_id>
       body JSON (almeno uno dei due campi richiesto):
         {"content_original"?: str, "author_name"?: str}
       -> 200 + {"id": message_id} se aggiornato
       -> 400 se body vuoto / nessun campo valido
       -> 404 se message_id non esiste

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
    msg_id = add_message(
        conn, scene_id=scene_id, author_name="Bob", content_original="testo originale",
        position_order=0,
    )
    conn.close()
    return {"path": str(p), "scene_id": scene_id, "msg_id": msg_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# --- WI-40: PATCH /api/db/messages/<id> -------------------------------------

def test_update_content_returns_200(client):
    c, s = client
    r = c.patch(f"/api/db/messages/{s['msg_id']}", json={"content_original": "testo aggiornato"})
    assert r.status_code == 200


def test_update_content_reflected(client):
    c, s = client
    c.patch(f"/api/db/messages/{s['msg_id']}", json={"content_original": "nuovo testo"})
    data = c.get(f"/api/db/messages/{s['msg_id']}").get_json()
    assert data["content_original"] == "nuovo testo"


def test_update_author_name_reflected(client):
    c, s = client
    c.patch(f"/api/db/messages/{s['msg_id']}", json={"author_name": "Alice"})
    data = c.get(f"/api/db/messages/{s['msg_id']}").get_json()
    assert data["author_name"] == "Alice"


def test_update_message_not_found_returns_404(client):
    c, _ = client
    r = c.patch("/api/db/messages/msg-inesistente", json={"content_original": "x"})
    assert r.status_code == 404


def test_update_message_empty_body_returns_400(client):
    c, s = client
    r = c.patch(f"/api/db/messages/{s['msg_id']}", json={})
    assert r.status_code == 400
