"""
Contract test (father-authored acceptance) — WI-57.

Il worker Efesto deve far passare questi test modificando in
`app/calliope_shell/scenes_db_routes.py` la route
GET /api/db/scenes/<scene_id>/characters (list_scene_characters):

    BUG: la route chiama direttamente list_characters_in_scene() senza
    verificare che la scena esista -> ritorna 200 + lista vuota per qualunque
    scene_id, anche inesistente.

    FIX: aggiungere check esistenza scena prima della chiamata:
        if conn.execute("SELECT 1 FROM scenes WHERE id=?", (scene_id,)).fetchone() is None:
            conn.close()
            return jsonify({"error": "not_found"}), 404
        chars = db_characters.list_characters_in_scene(conn, scene_id)

Questo allinea il comportamento con GET /api/db/scenes/<id> (che gia' ritorna 404)
e con GET /api/db/scenes/<id>/messages (che gia' verifica scena).

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
    register_scenes_db_routes(app, db_path=str(p))
    return app.test_client(), scene_id


# --- WI-57: GET characters per scena inesistente -> 404 ---------------------

def test_existing_scene_empty_roster_200(client):
    c, sid = client
    r = c.get(f"/api/db/scenes/{sid}/characters")
    assert r.status_code == 200
    assert r.get_json()["characters"] == []


def test_nonexistent_scene_returns_404(client):
    c, _ = client
    r = c.get("/api/db/scenes/scena-inesistente-xyz/characters")
    assert r.status_code == 404


def test_nonexistent_scene_returns_json_error(client):
    c, _ = client
    r = c.get("/api/db/scenes/scena-inesistente-xyz/characters")
    assert r.content_type == "application/json"
