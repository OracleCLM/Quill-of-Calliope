"""
Contract test (father-authored acceptance) — WI-30.

Il worker Efesto deve far passare questi test: casi limite della paginazione
messaggi in GET /api/db/scenes/<id>/messages (implementata in WI-12).

CONTRATTI edge-case da rispettare:
    ?page=99 su scena con 3 msg -> 200 + messages=[] (non 404)
    ?per_page=0 -> 400 (divisione per zero nel calcolo pages)
    ?page=0 -> 400 (page e' 1-based, 0 non valido)

Usa SOLO: db_messages.get_scene_message_page(conn, scene_id, page, per_page)
  app/db/messages.py:246 — gia' implementata.

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
                    content_original=f"m{i}", position_order=i)
    conn.close()
    return {"path": str(p), "scene_id": scene_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# --- WI-30: paginazione edge cases ------------------------------------------

def test_page_beyond_total_returns_empty_list(client):
    c, s = client
    r = c.get(f"/api/db/scenes/{s['scene_id']}/messages?page=99&per_page=10")
    assert r.status_code == 200
    data = r.get_json()
    assert data["messages"] == []
    assert data["total"] == 3


def test_per_page_zero_returns_400(client):
    c, s = client
    r = c.get(f"/api/db/scenes/{s['scene_id']}/messages?page=1&per_page=0")
    assert r.status_code == 400


def test_page_zero_returns_400(client):
    c, s = client
    r = c.get(f"/api/db/scenes/{s['scene_id']}/messages?page=0&per_page=10")
    assert r.status_code == 400


def test_negative_page_returns_400(client):
    c, s = client
    r = c.get(f"/api/db/scenes/{s['scene_id']}/messages?page=-1&per_page=10")
    assert r.status_code == 400
