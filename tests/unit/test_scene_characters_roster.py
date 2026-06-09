"""
Contract test (father-authored acceptance) — WI-15.

Il worker Efesto deve far passare questi test aggiungendo in
`app/calliope_shell/scenes_db_routes.py`:

    GET  /api/db/scenes/<scene_id>/characters
         -> 200 + {"characters": [...]}
    POST /api/db/scenes/<scene_id>/characters
         body JSON: {"character_id": "<id>", "role"?: str}
         -> 201 se aggiunto | 404 se scena o personaggio inesistente

Usa SOLO (aggiungere import in scenes_db_routes.py):
  from app.db import characters as db_characters
  db_characters.add_character_to_scene(conn, scene_id, character_id, role)
    -> app/db/characters.py:231
  db_characters.list_characters_in_scene(conn, scene_id)
    -> app/db/characters.py:262

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
    char_id = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "Scena"))
    conn.execute("INSERT INTO characters (id, name) VALUES (?, ?)", (char_id, "Luna"))
    conn.commit()
    conn.close()
    return {"path": str(p), "scene_id": scene_id, "char_id": char_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# --- WI-15: scene characters roster ------------------------------------------

def test_list_characters_in_scene_empty(client):
    c, s = client
    r = c.get(f"/api/db/scenes/{s['scene_id']}/characters")
    assert r.status_code == 200
    assert r.get_json()["characters"] == []


def test_add_character_to_scene_returns_201(client):
    c, s = client
    r = c.post(f"/api/db/scenes/{s['scene_id']}/characters",
               json={"character_id": s["char_id"]})
    assert r.status_code == 201


def test_add_character_appears_in_list(client):
    c, s = client
    c.post(f"/api/db/scenes/{s['scene_id']}/characters",
           json={"character_id": s["char_id"]})
    lst = c.get(f"/api/db/scenes/{s['scene_id']}/characters").get_json()["characters"]
    ids = [ch["id"] for ch in lst]
    assert s["char_id"] in ids


def test_add_character_unknown_scene_404(client):
    c, s = client
    r = c.post("/api/db/scenes/scena-inesistente/characters",
               json={"character_id": s["char_id"]})
    assert r.status_code == 404


def test_add_character_unknown_character_404(client):
    c, s = client
    r = c.post(f"/api/db/scenes/{s['scene_id']}/characters",
               json={"character_id": "char-inesistente"})
    assert r.status_code == 404
