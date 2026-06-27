"""GAP-70: test specifici per _verb_continua — direction fallback + response shape + gateway error."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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


def _mock_ok(text="testo generato"):
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"result": text}
    mock.raise_for_status = MagicMock()
    return mock


# ── response shape ────────────────────────────────────────────────────────────


def test_continua_response_has_action_field(client):
    with patch("requests.post", return_value=_mock_ok()):
        r = client.post("/api/write", json={
            "action": "continua",
            "scene_id": "s1",
            "intent_it": "prosegui la storia",
        })
    assert r.status_code == 200
    data = r.get_json()
    assert data["action"] == "continua"


def test_continua_response_has_draft_text(client):
    with patch("requests.post", return_value=_mock_ok("il mio testo")):
        r = client.post("/api/write", json={
            "action": "continua",
            "scene_id": "s1",
            "intent_it": "prosegui",
        })
    data = r.get_json()
    assert "draft_text" in data
    assert data["draft_text"] == "il mio testo"


# ── direction come alternativa a intent_it ────────────────────────────────────


def test_continua_accepts_direction_field(client):
    with patch("requests.post", return_value=_mock_ok()):
        r = client.post("/api/write", json={
            "action": "continua",
            "scene_id": "s1",
            "direction": "verso la foresta",
        })
    assert r.status_code == 200


# ── gateway error propagation ─────────────────────────────────────────────────


def test_continua_gateway_down_returns_503(client):
    import requests as _req
    with patch("requests.post", side_effect=_req.exceptions.ConnectionError):
        r = client.post("/api/write", json={
            "action": "continua",
            "scene_id": "s1",
            "intent_it": "prosegui",
        })
    assert r.status_code == 503
