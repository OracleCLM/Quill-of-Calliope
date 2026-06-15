"""
Contract test (father-authored acceptance) — WI-17.

Il worker Efesto deve far passare questi test aggiungendo in
`app/calliope_shell/scenes_db_routes.py`:

    GET /api/db/scenes/<scene_id>/messages/count
    -> 200 + {"count": N, "scene_id": "<id>"}
    -> 404 se la scena non esiste

Usa SOLO: db_messages.count_messages_for_scene(conn, scene_id) -> int
  app/db/messages.py:186 — gia' importata come db_messages.

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
    for i in range(3):
        add_message(conn, scene_id=scene_id, author_name=f"A{i}",
                    content_original=f"msg{i}", position_order=i)
    conn.close()
    return {"path": str(p), "scene_id": scene_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# --- WI-17: count messages ---------------------------------------------------

def test_count_returns_200(client):
    c, s = client
    r = c.get(f"/api/db/scenes/{s['scene_id']}/messages/count")
    assert r.status_code == 200


def test_count_correct_value(client):
    c, s = client
    data = c.get(f"/api/db/scenes/{s['scene_id']}/messages/count").get_json()
    assert data["count"] == 3
    assert data["scene_id"] == s["scene_id"]


def test_count_scene_not_found_404(client):
    c, _ = client
    r = c.get("/api/db/scenes/scena-inesistente/messages/count")
    assert r.status_code == 404


def test_count_zero_for_empty_scene(tmp_path):
    p = tmp_path / "empty.db"
    conn = get_db(p)
    init_schema(conn)
    scene_id = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "Vuota"))
    conn.commit()
    conn.close()
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=str(p))
    r = app.test_client().get(f"/api/db/scenes/{scene_id}/messages/count")
    assert r.status_code == 200
    assert r.get_json()["count"] == 0
