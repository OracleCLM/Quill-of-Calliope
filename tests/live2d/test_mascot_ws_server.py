"""WebSocket server tests — Phase-3. Uses Starlette TestClient (sync WS) + httpx AsyncClient."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
from mascot_ws_server import app  # noqa: E402


@pytest.fixture()
def client():
    return TestClient(app)


# ── HTTP tests ────────────────────────────────────────────────────────────────

def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "ok"
    assert isinstance(d["connected_clients"], int)


def test_post_state_event(client):
    r = client.post("/event/state", json={"state": "talking"})
    assert r.status_code == 200
    assert r.json()["status"] == "sent"


def test_post_emotion_event(client):
    r = client.post("/event/emotion", json={"emotion": "joy"})
    assert r.status_code == 200
    assert r.json()["status"] == "sent"


def test_post_tts_event(client):
    r = client.post("/event/tts", json={"type": "start", "data": {"text": "hello"}})
    assert r.status_code == 200
    assert r.json()["status"] == "sent"


# ── WebSocket tests ───────────────────────────────────────────────────────────

def test_ws_connect_welcome(client):
    with client.websocket_connect("/mascot") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "CONNECTED"
        assert "Calliope" in msg["msg"]


def test_ws_receives_state_broadcast(client):
    with client.websocket_connect("/mascot") as ws:
        ws.receive_json()  # consume welcome
        client.post("/event/state", json={"state": "talking"})
        msg = ws.receive_json()
        assert msg["type"] == "SET_STATE"
        assert msg["state"] == "talking"


def test_ws_receives_emotion_broadcast(client):
    with client.websocket_connect("/mascot") as ws:
        ws.receive_json()  # welcome
        client.post("/event/emotion", json={"emotion": "joy"})
        msg = ws.receive_json()
        assert msg["type"] == "SET_EXPRESSION"
        assert msg["expression"] == "joy"


def test_ws_multi_client_broadcast(client):
    with client.websocket_connect("/mascot") as ws1, \
         client.websocket_connect("/mascot") as ws2:
        ws1.receive_json()  # welcome
        ws2.receive_json()  # welcome
        client.post("/event/state", json={"state": "idle"})
        m1 = ws1.receive_json()
        m2 = ws2.receive_json()
        assert m1["type"] == m2["type"] == "SET_STATE"
        assert m1["state"] == m2["state"] == "idle"


def test_ws_disconnect_health(client):
    with client.websocket_connect("/mascot"):
        pass  # disconnect on exit
    r = client.get("/health")
    assert r.json()["connected_clients"] == 0
