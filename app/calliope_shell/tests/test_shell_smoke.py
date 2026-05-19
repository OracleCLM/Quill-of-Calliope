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


def test_root_renders_iframe(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"localhost:8001" in response.data


def test_mascot_state_get(client):
    response = client.get("/api/mascot/state")
    assert response.is_json
    data = response.get_json()
    assert "emotion" in data
    assert "ws_url" in data
