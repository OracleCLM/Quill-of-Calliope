"""
Test per GET /api/characters e GET /api/characters/<stem>
in app/calliope_shell/characters_routes.py.

L'upload immagine è già coperto da test_char_image_upload.py.
Qui mock characters_service per isolare la logica di routing.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from flask import Flask

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.characters_routes import register_character_routes

_SVC = "app.calliope_shell.characters_service"


@pytest.fixture
def client(tmp_path):
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    app = Flask(__name__, static_folder=str(static_dir))
    app.config["TESTING"] = True
    register_character_routes(app)
    return app.test_client()


# ── GET /api/characters ───────────────────────────────────────────────────────

def test_list_characters_empty(client):
    with patch(f"{_SVC}.list_cards", return_value=[]):
        r = client.get("/api/characters")
    assert r.status_code == 200
    assert r.get_json() == []


def test_list_characters_returns_list(client):
    cards = [
        {"stem": "aurora", "name": "Aurora", "compact": "Aurora — strega"},
        {"stem": "luna", "name": "Luna", "compact": "Luna — cacciatrice"},
    ]
    with patch(f"{_SVC}.list_cards", return_value=cards):
        r = client.get("/api/characters")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 2
    assert data[0]["name"] == "Aurora"


# ── GET /api/characters/<stem> ────────────────────────────────────────────────

def test_get_character_found(client):
    card = {"name": "Aurora", "personality": "strega", "tags": []}
    with patch(f"{_SVC}.get_card_v3", return_value=card):
        r = client.get("/api/characters/aurora")
    assert r.status_code == 200
    assert r.get_json()["name"] == "Aurora"


def test_get_character_not_found_404(client):
    with patch(f"{_SVC}.get_card_v3", return_value=None):
        r = client.get("/api/characters/ghost")
    assert r.status_code == 404
    assert "error" in r.get_json()


def test_get_character_returns_full_card(client):
    card = {"name": "Luna", "personality": "cacciatrice", "tags": ["ranger"], "description": "Hunter"}
    with patch(f"{_SVC}.get_card_v3", return_value=card):
        r = client.get("/api/characters/luna")
    data = r.get_json()
    assert data["personality"] == "cacciatrice"
    assert data["tags"] == ["ranger"]


# ── POST /api/characters (characters_create) ──────────────────────────────────

def test_create_character_invalid_name_all_symbols(client, tmp_path):
    """name composto solo da simboli → stem vuoto → 400 invalid name."""
    with patch(f"{_SVC}._chars_dir", return_value=tmp_path):
        r = client.post("/api/characters", json={"name": "---"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "invalid name"


def test_create_character_empty_name(client, tmp_path):
    """name vuoto → 400 name required."""
    with patch(f"{_SVC}._chars_dir", return_value=tmp_path):
        r = client.post("/api/characters", json={"name": ""})
    assert r.status_code == 400
    assert r.get_json()["error"] == "name required"


def test_create_character_success(client, tmp_path):
    """POST con name valido → 201 + stem."""
    with patch(f"{_SVC}._chars_dir", return_value=tmp_path):
        r = client.post("/api/characters", json={"name": "Aurora"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["stem"] == "aurora"
    assert data["name"] == "Aurora"


def test_create_character_already_exists(client, tmp_path):
    """POST con nome già esistente → 409 already exists."""
    (tmp_path / "aurora.draft.yaml").write_text("name: Aurora\n")
    with patch(f"{_SVC}._chars_dir", return_value=tmp_path):
        r = client.post("/api/characters", json={"name": "Aurora"})
    assert r.status_code == 409
    assert r.get_json()["error"] == "already exists"
