"""Sprint-A tests: /api/translate endpoint."""
from __future__ import annotations
from unittest.mock import patch, MagicMock
import pytest
from app.calliope_shell.server import create_app


@pytest.fixture()
def client():
    app, _ = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _mock_gateway_response(translation: str):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"result": translation}
    resp.raise_for_status = lambda: None
    return resp


def test_translate_endpoint_post(client):
    """Mock gateway returns translation — endpoint returns it correctly."""
    with patch("app.calliope_shell.server.requests.post",
               return_value=_mock_gateway_response("The sword gleams in the moonlight.")):
        r = client.post("/api/translate", json={
            "text": "La spada brilla alla luce della luna.",
            "direction": "IT_to_EN",
            "context": "fantasy_rp",
        })
    assert r.status_code == 200
    data = r.get_json()
    assert "translation" in data
    assert data["translation"] == "The sword gleams in the moonlight."
    assert "model_used" in data


def test_translate_direction_validation(client):
    """Invalid direction → 400."""
    r = client.post("/api/translate", json={
        "text": "Ciao",
        "direction": "FR_to_DE",
    })
    assert r.status_code == 400
    data = r.get_json()
    assert "error" in data


def test_translate_gateway_down(client):
    """Gateway ConnectionError → 503 fail-graceful."""
    import requests as req_module
    with patch("app.calliope_shell.server.requests.post",
               side_effect=req_module.exceptions.ConnectionError("refused")):
        r = client.post("/api/translate", json={
            "text": "Test text",
            "direction": "IT_to_EN",
        })
    assert r.status_code == 503
    data = r.get_json()
    assert "error" in data
    assert data.get("code") == "gateway_down"
