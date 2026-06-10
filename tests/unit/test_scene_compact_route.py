"""
Contract test (father-authored acceptance) — WI-25.

Il worker Efesto deve far passare questi test aggiungendo in
`app/calliope_shell/scenes_db_routes.py`:

    POST /api/db/scenes/<scene_id>/messages/compact
    -> 200 + {"count": N}   (N = numero messaggi dopo compacting)
    -> 404 se scene_id non esiste

NOTA: compact_scene_positions riassegna position_order da 1 in sequenza
continua, eliminando gap (es. 0,2,5 -> 1,2,3). Non rimuove messaggi.

Usa SOLO: db_messages.compact_scene_positions(conn, scene_id) -> int
  app/db/messages.py:400 — ritorna numero messaggi compattati.

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema, new_id
from app.calliope_shell.scenes_db_routes import register_scenes_db_routes


def _make_scene_with_gaps(conn):
    """Crea una scena con gap nelle position_order: 0, 5, 10."""
    scene_id = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "Gap"))
    conn.commit()
    for pos in (0, 5, 10):
        conn.execute(
            "INSERT INTO messages"
            " (id, scene_id, author_name, content_original, ts, position_order)"
            " VALUES (?, ?, ?, ?, datetime('now'), ?)",
            (new_id(), scene_id, "A", f"msg@{pos}", pos),
        )
    conn.commit()
    return scene_id


@pytest.fixture
def seeded(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    scene_id = _make_scene_with_gaps(conn)
    conn.close()
    return {"path": str(p), "scene_id": scene_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# --- WI-25: compact scene positions -----------------------------------------

def test_compact_returns_200(client):
    c, s = client
    r = c.post(f"/api/db/scenes/{s['scene_id']}/messages/compact")
    assert r.status_code == 200


def test_compact_returns_correct_count(client):
    c, s = client
    data = c.post(f"/api/db/scenes/{s['scene_id']}/messages/compact").get_json()
    assert data["count"] == 3


def test_compact_does_not_remove_messages(client):
    c, s = client
    c.post(f"/api/db/scenes/{s['scene_id']}/messages/compact")
    detail = c.get(f"/api/db/scenes/{s['scene_id']}").get_json()
    assert len(detail["messages"]) == 3


def test_compact_scene_not_found_404(client):
    c, _ = client
    r = c.post("/api/db/scenes/scena-inesistente/messages/compact")
    assert r.status_code == 404
