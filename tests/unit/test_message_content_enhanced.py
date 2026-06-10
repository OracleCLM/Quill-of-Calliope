"""
Contract test (father-authored acceptance) — WI-45.

Il worker Efesto deve far passare questi test modificando in
`app/calliope_shell/scenes_db_routes.py` la route
POST /api/db/scenes/<scene_id>/messages:

    Leggere dal body JSON il campo opzionale "content_enhanced" e passarlo
    a db_messages.add_message(..., content_enhanced=body.get("content_enhanced")).

    La route attuale ignora content_enhanced (non lo passa ad add_message).

Usa SOLO: il parametro content_enhanced gia' accettato da add_message
  app/db/messages.py:27 — content_enhanced: Optional[str] = None.

Flusso operativo: POST salva il draft Cerebras in content_enhanced,
  GET /api/db/messages/<id> lo restituisce nel dizionario.

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema, new_id
from app.calliope_shell.scenes_db_routes import register_scenes_db_routes


@pytest.fixture
def seeded(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    scene_id = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "S"))
    conn.commit()
    conn.close()
    return {"path": str(p), "scene_id": scene_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


def _post_message(c, scene_id, **kwargs):
    payload = {
        "author_name": "Alice",
        "content_original": "testo italiano",
        **kwargs,
    }
    return c.post(f"/api/db/scenes/{scene_id}/messages", json=payload).get_json()["id"]


# --- WI-45: content_enhanced salvato e restituito ---------------------------

def test_message_without_enhanced_stores_null(client):
    c, s = client
    mid = _post_message(c, s["scene_id"])
    data = c.get(f"/api/db/messages/{mid}").get_json()
    assert "content_enhanced" in data
    assert data["content_enhanced"] is None


def test_message_with_enhanced_stored(client):
    c, s = client
    mid = _post_message(
        c, s["scene_id"],
        content_enhanced="The Italian text, rendered in literary English.",
    )
    data = c.get(f"/api/db/messages/{mid}").get_json()
    assert data["content_enhanced"] == "The Italian text, rendered in literary English."


def test_enhanced_independent_from_original(client):
    c, s = client
    mid = _post_message(
        c, s["scene_id"],
        content_original="ciao mondo",
        content_enhanced="Hello, world.",
    )
    data = c.get(f"/api/db/messages/{mid}").get_json()
    assert data["content_original"] == "ciao mondo"
    assert data["content_enhanced"] == "Hello, world."
