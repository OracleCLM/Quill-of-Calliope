import pytest

from app.calliope_shell.server import create_app


@pytest.fixture
def client():
    app, _ = create_app()
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_root_renders_iframe(client, monkeypatch):
    # Hermetic: force st_alive=True so the ST iframe renders without depending
    # on a live SillyTavern at :8001 (the / route HEAD-probes ST_URL).
    class _Resp:
        status_code = 200

    monkeypatch.setattr(
        "app.calliope_shell.server.requests.head", lambda *a, **k: _Resp()
    )
    response = client.get("/")
    assert response.status_code == 200
    assert b"localhost:8001" in response.data


def test_mascot_state_get(client):
    response = client.get("/api/mascot/state")
    assert response.is_json
    data = response.get_json()
    assert "emotion" in data
    assert "ws_url" in data


def test_root_st_unreachable(client, monkeypatch):
    """Lines 220-221: except branch quando ST non è raggiungibile."""
    monkeypatch.setattr(
        "app.calliope_shell.server.requests.head",
        lambda *a, **k: (_ for _ in ()).throw(ConnectionError("unreachable")),
    )
    response = client.get("/")
    assert response.status_code == 200


def test_mascot_emotion_map(client):
    """Lines 190-195: _load_emotion_map via GET /api/mascot/emotion_map."""
    response = client.get("/api/mascot/emotion_map")
    assert response.status_code == 200
    assert response.is_json


def test_mascot_emotion_map_missing_file(client, monkeypatch, tmp_path):
    """Lines 193-195: except branch in _load_emotion_map quando file mancante."""
    import app.calliope_shell.server as srv
    monkeypatch.setattr(srv.Path, "read_text", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("no file")))
    response = client.get("/api/mascot/emotion_map")
    assert response.status_code == 200
    assert response.get_json() == {}
