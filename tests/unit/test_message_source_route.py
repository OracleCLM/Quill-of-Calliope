"""
Contract test (father-authored acceptance) — WI-50.

Il worker Efesto deve far passare questi test modificando in
`app/calliope_shell/scenes_db_routes.py` la route
POST /api/db/scenes/<scene_id>/messages:

    Leggere il campo opzionale "source" dal body JSON (default: "manual")
    e passarlo a db_messages.add_message(..., source=body.get("source", "manual")).

    Valori attesi in produzione: "manual" (input diretto), "discord" (bot),
    "import" (dataset storico), "draft" (bozza Cerebras).
    La route NON valida il valore — lo memorizza opaco.

Usa SOLO: il parametro source gia' accettato da add_message
  app/db/messages.py:27 — source: str = "manual".

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


# --- WI-50: source field via route POST/GET ---------------------------------

def test_message_default_source_is_manual(client):
    c, s = client
    mid = _post_msg(c, s["scene_id"])
    data = c.get(f"/api/db/messages/{mid}").get_json()
    assert "source" in data
    assert data["source"] == "manual"


def test_message_discord_source_stored(client):
    c, s = client
    mid = _post_msg(c, s["scene_id"], source="discord")
    data = c.get(f"/api/db/messages/{mid}").get_json()
    assert data["source"] == "discord"


def test_message_import_source_stored(client):
    c, s = client
    mid = _post_msg(c, s["scene_id"], source="import")
    data = c.get(f"/api/db/messages/{mid}").get_json()
    assert data["source"] == "import"
