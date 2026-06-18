"""GAP-74: test per /api/mascot/state e /api/mascot/emotion_map."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from app.calliope_shell.server import create_app


@pytest.fixture
def client():
    app, _ = create_app()
    app.config["TESTING"] = True
    return app.test_client()


# ── GET /api/mascot/state ─────────────────────────────────────────────────────


def test_mascot_state_get_returns_200(client):
    r = client.get("/api/mascot/state")
    assert r.status_code == 200


def test_mascot_state_get_has_emotion(client):
    data = client.get("/api/mascot/state").get_json()
    assert "emotion" in data


def test_mascot_state_get_has_intensity(client):
    data = client.get("/api/mascot/state").get_json()
    assert "intensity" in data


def test_mascot_state_get_default_emotion_neutral(client):
    data = client.get("/api/mascot/state").get_json()
    assert data["emotion"] == "neutral"


# ── POST /api/mascot/state ────────────────────────────────────────────────────


def test_mascot_state_post_returns_ok(client):
    with patch("requests.post", side_effect=RuntimeError("no WS")):
        r = client.post("/api/mascot/state", json={"emotion": "happy"})
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_mascot_state_post_updates_emotion(client):
    with patch("requests.post", side_effect=RuntimeError("no WS")):
        client.post("/api/mascot/state", json={"emotion": "sad", "intensity": 0.5})
        data = client.get("/api/mascot/state").get_json()
    assert data["emotion"] == "sad"
    assert data["intensity"] == 0.5


def test_mascot_state_post_ws_failure_non_fatal(client):
    import requests as _req
    with patch("requests.post", side_effect=_req.exceptions.ConnectionError):
        r = client.post("/api/mascot/state", json={"emotion": "angry"})
    assert r.status_code == 200


# ── GET /api/mascot/emotion_map ───────────────────────────────────────────────


def test_mascot_emotion_map_returns_200(client):
    r = client.get("/api/mascot/emotion_map")
    assert r.status_code == 200


def test_mascot_emotion_map_returns_dict(client):
    data = client.get("/api/mascot/emotion_map").get_json()
    assert isinstance(data, dict)
