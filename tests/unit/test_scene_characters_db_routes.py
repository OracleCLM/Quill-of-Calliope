"""GAP-82: test per /api/db/scenes/<id>/characters (GET/POST/PATCH/DELETE)."""

import sys
from pathlib import Path

import pytest
from flask import Flask

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.scene_characters_db_routes import register_scene_characters_db_routes
from app.db import get_db, init_schema, new_id


@pytest.fixture
def client(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    conn.close()
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scene_characters_db_routes(app, db_path=str(p))
    return app.test_client(), str(p)


def _setup(db_path):
    conn = get_db(db_path)
    scene_id = new_id()
    char_id = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "Scena Test"))
    conn.execute("INSERT INTO characters (id, name) VALUES (?, ?)", (char_id, "Aurora"))
    conn.commit()
    conn.close()
    return scene_id, char_id


def test_list_chars_scene_not_found(client):
    c, _ = client
    r = c.get("/api/db/scenes/nonexistent/characters")
    assert r.status_code == 404


def test_list_chars_empty_scene(client):
    c, db = client
    scene_id, _ = _setup(db)
    data = c.get(f"/api/db/scenes/{scene_id}/characters").get_json()
    assert "characters" in data
    assert isinstance(data["characters"], list)


def test_add_char_scene_not_found(client):
    c, _ = client
    r = c.post("/api/db/scenes/nonexistent/characters", json={"character_id": "x"})
    assert r.status_code == 404


def test_add_char_missing_char_id_returns_400(client):
    c, db = client
    scene_id, _ = _setup(db)
    r = c.post(f"/api/db/scenes/{scene_id}/characters", json={})
    assert r.status_code == 400


def test_add_char_char_not_found_returns_404(client):
    c, db = client
    scene_id, _ = _setup(db)
    r = c.post(f"/api/db/scenes/{scene_id}/characters", json={"character_id": "missing-char"})
    assert r.status_code == 404


def test_add_char_ok_returns_201(client):
    c, db = client
    scene_id, char_id = _setup(db)
    r = c.post(f"/api/db/scenes/{scene_id}/characters", json={"character_id": char_id})
    assert r.status_code == 201


def test_add_char_duplicate_returns_409(client):
    c, db = client
    scene_id, char_id = _setup(db)
    c.post(f"/api/db/scenes/{scene_id}/characters", json={"character_id": char_id})
    r = c.post(f"/api/db/scenes/{scene_id}/characters", json={"character_id": char_id})
    assert r.status_code == 409


def test_add_char_appears_in_list(client):
    c, db = client
    scene_id, char_id = _setup(db)
    c.post(f"/api/db/scenes/{scene_id}/characters", json={"character_id": char_id})
    data = c.get(f"/api/db/scenes/{scene_id}/characters").get_json()
    # list_characters_in_scene returns full characters rows (id, name, ...) + role
    ids = [ch["id"] for ch in data["characters"]]
    assert char_id in ids


def test_patch_role_missing_role_returns_400(client):
    c, db = client
    scene_id, char_id = _setup(db)
    c.post(f"/api/db/scenes/{scene_id}/characters", json={"character_id": char_id})
    r = c.patch(f"/api/db/scenes/{scene_id}/characters/{char_id}", json={})
    assert r.status_code == 400


def test_delete_char_from_scene_returns_204(client):
    c, db = client
    scene_id, char_id = _setup(db)
    c.post(f"/api/db/scenes/{scene_id}/characters", json={"character_id": char_id})
    r = c.delete(f"/api/db/scenes/{scene_id}/characters/{char_id}")
    assert r.status_code == 204


def test_delete_char_not_found_returns_404(client):
    c, db = client
    scene_id, _ = _setup(db)
    r = c.delete(f"/api/db/scenes/{scene_id}/characters/nonexistent-char")
    assert r.status_code == 404
