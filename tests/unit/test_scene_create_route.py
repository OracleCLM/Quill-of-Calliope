"""GAP-63: test per POST /api/db/scenes — db_create_scene route."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from flask import Flask

from app.calliope_shell.scenes_db_routes import register_scenes_db_routes
from app.db import get_db, init_schema


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test.db"
    conn = get_db(db_path)
    init_schema(conn)
    conn.close()
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=str(db_path))
    with app.test_client() as c:
        yield c


# ── POST /api/db/scenes ───────────────────────────────────────────────────────


def test_create_scene_returns_201(client):
    r = client.post("/api/db/scenes", json={"title": "Nuova Scena"})
    assert r.status_code == 201


def test_create_scene_returns_id(client):
    r = client.post("/api/db/scenes", json={"title": "Scena con ID"})
    data = r.get_json()
    assert "id" in data
    assert data["id"]


def test_create_scene_returns_title(client):
    r = client.post("/api/db/scenes", json={"title": "Foresta Oscura"})
    data = r.get_json()
    assert data["title"] == "Foresta Oscura"


def test_create_scene_missing_title_returns_400(client):
    r = client.post("/api/db/scenes", json={})
    assert r.status_code == 400


def test_create_scene_empty_title_returns_400(client):
    r = client.post("/api/db/scenes", json={"title": ""})
    assert r.status_code == 400


def test_create_scene_null_title_returns_400(client):
    r = client.post("/api/db/scenes", json={"title": None})
    assert r.status_code == 400


def test_create_scene_with_location(client):
    r = client.post("/api/db/scenes", json={"title": "Dungeon", "location": "Caverna Nord"})
    data = r.get_json()
    assert data["location"] == "Caverna Nord"


def test_create_scene_without_location_returns_none(client):
    r = client.post("/api/db/scenes", json={"title": "Scena senza luogo"})
    data = r.get_json()
    assert data["location"] is None


def test_create_scene_appears_in_list(client):
    client.post("/api/db/scenes", json={"title": "Scena Visibile"})
    r = client.get("/api/db/scenes")
    scenes = r.get_json().get("scenes") or r.get_json()
    titles = [s["title"] for s in scenes]
    assert "Scena Visibile" in titles


def test_create_scene_unique_ids(client):
    r1 = client.post("/api/db/scenes", json={"title": "A"})
    r2 = client.post("/api/db/scenes", json={"title": "B"})
    assert r1.get_json()["id"] != r2.get_json()["id"]


def test_create_scene_no_json_body_returns_400(client):
    r = client.post("/api/db/scenes", content_type="application/json", data="")
    assert r.status_code == 400
