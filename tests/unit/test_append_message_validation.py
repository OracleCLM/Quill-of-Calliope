"""
Contract test (father-authored acceptance) — WI-54.

Il worker Efesto deve far passare questi test modificando in
`app/calliope_shell/scenes_db_routes.py` la route
POST /api/db/scenes/<scene_id>/messages (db_append_message):

    BUG: la route usa body["author_name"] e body["content_original"] senza
    validazione preventiva -> KeyError -> 500 se i campi mancano.

    FIX: validare prima di accedere ai campi:
        body = request.get_json(force=True) or {}
        author_name = body.get("author_name", "").strip()
        content_original = body.get("content_original")
        if not author_name or content_original is None:
            conn.close()
            return jsonify({"error": "bad_request"}), 400

Comportamenti da correggere:
  - body senza "author_name"     -> 400 (attuale: 500 KeyError)
  - body senza "content_original"-> 400 (attuale: 500 KeyError)
  - author_name stringa vuota "" -> 400 (attuale: 201 — messaggio senza autore)
  - body vuoto {}                -> 400 (attuale: 500)

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema, new_id
from app.calliope_shell.scenes_db_routes import register_scenes_db_routes


@pytest.fixture
def client(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    scene_id = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "S"))
    conn.commit()
    conn.close()
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["PROPAGATE_EXCEPTIONS"] = False
    register_scenes_db_routes(app, db_path=str(p))
    return app.test_client(), scene_id


# --- WI-54: validazione campi obbligatori POST messages ---------------------

def test_missing_author_name_returns_400(client):
    c, sid = client
    r = c.post(f"/api/db/scenes/{sid}/messages",
               json={"content_original": "ciao"})
    assert r.status_code == 400


def test_missing_content_original_returns_400(client):
    c, sid = client
    r = c.post(f"/api/db/scenes/{sid}/messages",
               json={"author_name": "Alice"})
    assert r.status_code == 400


def test_empty_author_name_returns_400(client):
    c, sid = client
    r = c.post(f"/api/db/scenes/{sid}/messages",
               json={"author_name": "", "content_original": "ciao"})
    assert r.status_code == 400


def test_empty_body_returns_400(client):
    c, sid = client
    r = c.post(f"/api/db/scenes/{sid}/messages", json={})
    assert r.status_code == 400


def test_valid_payload_still_returns_201(client):
    c, sid = client
    r = c.post(f"/api/db/scenes/{sid}/messages",
               json={"author_name": "Alice", "content_original": "ciao"})
    assert r.status_code == 201
