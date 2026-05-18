"""Mascot WS + emotion sync tests — Sprint 3."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
from mascot_ws_server import app  # noqa: E402


@pytest.fixture()
def ws_client():
    return TestClient(app)


# ── test 1: WS server broadcasts emotion ─────────────────────────────────────

def test_ws_server_broadcasts_emotion(ws_client):
    """Mock client sends emotion via REST; WS client receives SET_EXPRESSION broadcast."""
    with ws_client.websocket_connect("/mascot") as ws:
        ws.receive_json()  # consume CONNECTED welcome
        r = ws_client.post("/event/emotion", json={"emotion": "determined"})
        assert r.status_code == 200
        msg = ws.receive_json()
        assert msg["type"] == "SET_EXPRESSION"
        assert msg["expression"] == "determined"


# ── test 2: emotion_map YAML loads and is non-empty ──────────────────────────

def test_emotion_map_loads():
    """aurora_emotion_map.yaml parses correctly and has required keys."""
    map_path = Path(__file__).parents[2] / "data" / "aurora_emotion_map.yaml"
    assert map_path.exists(), f"aurora_emotion_map.yaml not found at {map_path}"
    data = yaml.safe_load(map_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "YAML must parse to dict"
    assert "expressions" in data, "Missing 'expressions' key"
    assert "motions" in data, "Missing 'motions' key"
    assert "scene_type_emotion" in data, "Missing 'scene_type_emotion' key"
    assert len(data["expressions"]) > 0, "expressions map must be non-empty"
    assert "determined" in data["expressions"], "Expected 'determined' in expressions"


# ── test 3: generate_scene publishes emotion (mocked HTTP) ───────────────────

def test_generate_scene_publishes_emotion(tmp_path):
    """generate_scene._publish_emotion calls requests.post with correct payload."""
    sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
    import generate_scene as gs  # noqa: PLC0415

    captured = {}

    def mock_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        resp = MagicMock()
        resp.raise_for_status = lambda: None
        return resp

    with patch("generate_scene.requests.post", side_effect=mock_post):
        gs._publish_emotion("determined", 0.9, "scene_001", "http://localhost:5000")

    assert "url" in captured, "_publish_emotion did not call requests.post"
    assert captured["url"] == "http://localhost:5000/api/mascot/state"
    assert captured["json"]["emotion"] == "determined"
    assert captured["json"]["intensity"] == pytest.approx(0.9)
    assert captured["json"]["scene_id"] == "scene_001"
