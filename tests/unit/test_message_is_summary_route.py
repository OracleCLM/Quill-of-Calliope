"""
Contract test (father-authored acceptance) — WI-49.

Il worker Efesto deve far passare questi test modificando in
`app/calliope_shell/scenes_db_routes.py` la route
POST /api/db/scenes/<scene_id>/messages:

    Leggere il campo opzionale "is_summary" dal body JSON (default: 0)
    e passarlo a db_messages.add_message(..., is_summary=body.get("is_summary", 0)).

    Uso operativo: messaggi marcati come is_summary=1 sono riassunti di sessione
    che il sistema puo' usare per comprimere contesto lungo nelle chiamate LLM.

Usa SOLO: il parametro is_summary gia' accettato da add_message
  app/db/messages.py:27 — is_summary: int = 0.

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


def _post_msg(c, scene_id, **extra):
    payload = {"author_name": "A", "content_original": "x", **extra}
    return c.post(f"/api/db/scenes/{scene_id}/messages", json=payload).get_json()["id"]


# --- WI-49: is_summary flag via route POST/GET ------------------------------

def test_message_without_is_summary_defaults_to_zero(client):
    c, s = client
    mid = _post_msg(c, s["scene_id"])
    data = c.get(f"/api/db/messages/{mid}").get_json()
    assert "is_summary" in data
    assert data["is_summary"] == 0


def test_message_with_is_summary_one_stored(client):
    c, s = client
    mid = _post_msg(c, s["scene_id"], is_summary=1)
    data = c.get(f"/api/db/messages/{mid}").get_json()
    assert data["is_summary"] == 1


def test_is_summary_zero_explicit(client):
    c, s = client
    mid = _post_msg(c, s["scene_id"], is_summary=0)
    data = c.get(f"/api/db/messages/{mid}").get_json()
    assert data["is_summary"] == 0
