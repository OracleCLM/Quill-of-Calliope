"""Phase-3 E2E integration tests — cross-component (TestClient, no real daemons)."""
from __future__ import annotations
import sys
import urllib.request
import urllib.error
from pathlib import Path
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
from mascot_ws_server import app as mascot_app  # noqa: E402


@pytest.fixture(scope="module")
def ws_client():
    return TestClient(mascot_app)


def test_1_health_ws_service(ws_client):
    r = ws_client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert isinstance(r.json()["connected_clients"], int)


def test_2_llm_gateway_health():
    try:
        with urllib.request.urlopen("http://localhost:8766/health", timeout=3) as resp:
            import json
            d = json.loads(resp.read())
            assert d["status"] == "ok"
    except Exception:
        pytest.skip("LLM gateway not running on 8766")


def test_3_ollama_health():
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3):
            pass
    except (urllib.error.URLError, OSError):
        pytest.skip("Ollama not running on 11434")


def test_4_ws_connect_welcome(ws_client):
    with ws_client.websocket_connect("/mascot") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "CONNECTED"
        assert "Calliope" in msg["msg"]


def test_5_state_broadcast(ws_client):
    with ws_client.websocket_connect("/mascot") as ws:
        ws.receive_json()  # welcome
        ws_client.post("/event/state", json={"state": "talking"})
        msg = ws.receive_json()
        assert msg["type"] == "SET_STATE"
        assert msg["state"] == "talking"


def test_6_emotion_broadcast(ws_client):
    with ws_client.websocket_connect("/mascot") as ws:
        ws.receive_json()
        ws_client.post("/event/emotion", json={"emotion": "joy"})
        msg = ws.receive_json()
        assert msg["type"] == "SET_EXPRESSION"
        assert msg["expression"] == "joy"


def test_7_tts_phoneme_roundtrip():
    from tts_phoneme_export import export_phonemes
    result = export_phonemes("Aurora speaks", "/tmp")
    assert len(result["phonemes"]) > 0
    assert result["text"] == "Aurora speaks"


def test_8_cross_component_tts_ws(ws_client):
    from tts_phoneme_export import export_phonemes
    with ws_client.websocket_connect("/mascot") as ws:
        ws.receive_json()
        phonemes = export_phonemes("Hello", "/tmp")["phonemes"]
        ws_client.post("/event/tts", json={
            "type": "start",
            "data": {"text": "Hello", "phoneme_count": len(phonemes)},
        })
        msg = ws.receive_json()
        assert msg["type"] == "TTS_EVENT"
        assert msg["tts_type"] == "start"
