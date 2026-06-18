"""GAP-20: test contratto per POST /api/write dispatch routing."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from flask import Flask

from app.calliope_shell.write_routes import register_write_routes


@pytest.fixture
def client():
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_write_routes(app)
    return app.test_client()


# --- dispatch guard -------------------------------------------------------


def test_missing_action_returns_400(client):
    r = client.post("/api/write", json={})
    assert r.status_code == 400
    assert "action" in r.get_json()["error"]


def test_invalid_action_returns_400(client):
    r = client.post("/api/write", json={"action": "inventato"})
    assert r.status_code == 400


def test_valid_actions_listed_in_error(client):
    r = client.post("/api/write", json={"action": "xyz"})
    body = r.get_json()["error"]
    for verb in ("genera", "continua", "rifinisci", "traduci", "riassumi", "coerenza"):
        assert verb in body


# --- routing per ogni verbo (gateway mockato) ----------------------------


def _mock_ok(text="risposta mock"):
    from unittest.mock import MagicMock
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"result": text}
    mock.raise_for_status = MagicMock()
    return mock


@pytest.mark.parametrize("action", ["genera", "continua", "rifinisci", "riassumi"])
def test_verb_routes_to_handler(client, action):
    with patch("requests.post", return_value=_mock_ok()):
        r = client.post("/api/write", json={
            "action": action,
            "scene_id": "scene_test",
            "text": "testo di prova",
            "intent_it": "scrivi una scena breve",
        })
    assert r.status_code == 200
    assert r.get_json() is not None


def test_verb_traduci_routes(client):
    with patch("requests.post", return_value=_mock_ok("translation mock")):
        r = client.post("/api/write", json={
            "action": "traduci",
            "text": "testo da tradurre",
            "direction": "IT_to_EN",
        })
    assert r.status_code == 200


def test_verb_coerenza_routes(client):
    with patch("requests.post", return_value=_mock_ok('{"coherent": true, "issues": []}')):
        r = client.post("/api/write", json={
            "action": "coerenza",
            "scene_id": "scene_test",
            "text": "testo da verificare",
        })
    assert r.status_code == 200
