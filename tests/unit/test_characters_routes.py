"""GAP-51: test per register_character_routes — GET/POST /api/characters + GET /<stem>."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from flask import Flask

from app.calliope_shell.characters_routes import register_character_routes


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", str(tmp_path))
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["STATIC_FOLDER"] = str(tmp_path / "static")
    register_character_routes(app)
    return app.test_client()


# ── GET /api/characters ───────────────────────────────────────────────────────


def test_list_returns_200(client):
    r = client.get("/api/characters")
    assert r.status_code == 200


def test_list_empty_initially(client):
    data = client.get("/api/characters").get_json()
    assert data == []


def test_list_returns_created_character(client):
    client.post("/api/characters", json={"name": "Aurora"})
    data = client.get("/api/characters").get_json()
    assert any(c.get("name") == "Aurora" for c in data)


# ── POST /api/characters ──────────────────────────────────────────────────────


def test_create_returns_201(client):
    r = client.post("/api/characters", json={"name": "Mao"})
    assert r.status_code == 201


def test_create_missing_name_returns_400(client):
    r = client.post("/api/characters", json={})
    assert r.status_code == 400


def test_create_empty_name_returns_400(client):
    r = client.post("/api/characters", json={"name": "  "})
    assert r.status_code == 400


def test_create_returns_stem(client):
    data = client.post("/api/characters", json={"name": "Kira"}).get_json()
    assert "stem" in data and data["stem"]


def test_create_returns_name(client):
    data = client.post("/api/characters", json={"name": "Zoe"}).get_json()
    assert data["name"] == "Zoe"


def test_create_no_json_body_returns_400(client):
    r = client.post("/api/characters", data="notjson", content_type="text/plain")
    assert r.status_code == 400


# ── GET /api/characters/<stem> ────────────────────────────────────────────────


def test_get_existing_character(client):
    stem = client.post("/api/characters", json={"name": "Elara"}).get_json()["stem"]
    r = client.get(f"/api/characters/{stem}")
    assert r.status_code == 200


def test_get_missing_character_returns_404(client):
    r = client.get("/api/characters/inesistente-stem")
    assert r.status_code == 404


def test_get_character_has_name(client):
    stem = client.post("/api/characters", json={"name": "Fiora"}).get_json()["stem"]
    data = client.get(f"/api/characters/{stem}").get_json()
    assert data.get("data", {}).get("name") or data.get("name")
