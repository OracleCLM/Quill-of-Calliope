"""
Contract test (father-authored acceptance) — WI-68.

Una scena con `is_readonly = 1` (scene legacy importate da dataset) NON deve
accettare nuovi messaggi. Il worker Efesto deve aggiungere il guard in
`app/calliope_shell/messages_db_routes.py` sull'handler:

    POST /api/db/scenes/<scene_id>/messages
      -> 403 + {"error": ...} se la scena ha is_readonly = 1
      (comportamento invariato per scene scrivibili: 201)

Usa SOLO: from app.db import get_db; e la colonna scenes.is_readonly già
presente nello schema (migrations/001_scene_as_chat.sql).
NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema
from app.calliope_shell.scenes_db_routes import register_scenes_db_routes


@pytest.fixture
def ctx(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    conn.close()
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=str(p))
    return app.test_client(), str(p)


def _make_scene(client, title="Legacy Scene"):
    r = client.post("/api/db/scenes", json={"title": title})
    assert r.status_code == 201
    return r.get_json()["id"]


def _set_readonly(db_path, scene_id):
    conn = get_db(db_path)
    conn.execute("UPDATE scenes SET is_readonly = 1 WHERE id = ?", (scene_id,))
    conn.commit()
    conn.close()


# --- WI-68: POST message su scena read-only -> 403 --------------------------

def test_post_message_to_readonly_scene_is_forbidden(ctx):
    client, db_path = ctx
    scene_id = _make_scene(client)
    _set_readonly(db_path, scene_id)
    r = client.post(
        f"/api/db/scenes/{scene_id}/messages",
        json={"author_name": "Nic", "content_original": "hello"},
    )
    assert r.status_code == 403


def test_post_message_to_writable_scene_still_works(ctx):
    client, db_path = ctx
    scene_id = _make_scene(client)
    r = client.post(
        f"/api/db/scenes/{scene_id}/messages",
        json={"author_name": "Nic", "content_original": "hello"},
    )
    assert r.status_code == 201
