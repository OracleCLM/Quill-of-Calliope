"""
Contract test (father-authored acceptance) — WI-12.

Il worker Efesto deve far passare questi test aggiungendo in
`app/calliope_shell/scenes_db_routes.py`:

    GET /api/db/scenes/<scene_id>/messages?page=N&per_page=M
    - 200 + {"messages": [...], "page": N, "per_page": M, "total": T, "pages": P}
    - page e per_page hanno default (1, 50) se assenti
    - 404 se la scena non esiste

Usa SOLO: app.db.messages.get_scene_message_page(conn, scene_id, page, per_page)
(già implementata, ritorna {messages, page, per_page, total, pages})

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema, new_id
from app.db.messages import add_message
from app.calliope_shell.scenes_db_routes import register_scenes_db_routes


@pytest.fixture
def seeded(tmp_path):
    """Scena con 5 messaggi per testare la paginazione."""
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    scene_id = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "Pagina"))
    conn.commit()
    for i in range(5):
        add_message(conn, scene_id=scene_id, author_name=f"Char{i}",
                    content_original=f"msg {i}", position_order=i)
    conn.close()
    return {"path": str(p), "scene_id": scene_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# --- WI-12: paginazione messaggi ---------------------------------------------

def test_page1_returns_first_two(client):
    c, s = client
    r = c.get(f"/api/db/scenes/{s['scene_id']}/messages?page=1&per_page=2")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data["messages"]) == 2
    assert data["total"] == 5
    assert data["pages"] == 3
    assert data["page"] == 1


def test_last_page_returns_remainder(client):
    c, s = client
    r = c.get(f"/api/db/scenes/{s['scene_id']}/messages?page=3&per_page=2")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data["messages"]) == 1


def test_default_page_returns_all(client):
    c, s = client
    r = c.get(f"/api/db/scenes/{s['scene_id']}/messages")
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 5
    assert len(data["messages"]) == 5  # default per_page=50 > 5


def test_pagination_response_shape(client):
    c, s = client
    r = c.get(f"/api/db/scenes/{s['scene_id']}/messages?page=1&per_page=3")
    data = r.get_json()
    assert all(k in data for k in ("messages", "page", "per_page", "total", "pages"))
    assert data["per_page"] == 3


def test_scene_not_found_404(client):
    c, _ = client
    r = c.get("/api/db/scenes/non-esiste/messages?page=1&per_page=10")
    assert r.status_code == 404
