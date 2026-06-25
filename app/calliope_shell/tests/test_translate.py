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


def test_translate_it_to_en_generic_context(client):
    """Line 512: IT_to_EN con context != fantasy_rp → sistema generico."""
    with patch("app.calliope_shell.server.requests.post",
               return_value=_mock_gateway_response("Hello.")):
        r = client.post("/api/translate", json={
            "text": "Ciao.",
            "direction": "IT_to_EN",
            "context": "generic",
        })
    assert r.status_code == 200


def test_translate_en_to_it_fantasy_rp(client):
    """Lines 515-521: EN_to_IT con context=fantasy_rp → sistema fantasy."""
    with patch("app.calliope_shell.server.requests.post",
               return_value=_mock_gateway_response("La spada brilla.")):
        r = client.post("/api/translate", json={
            "text": "The sword gleams.",
            "direction": "EN_to_IT",
            "context": "fantasy_rp",
        })
    assert r.status_code == 200
    assert r.get_json()["translation"] == "La spada brilla."


def test_translate_en_to_it_generic_context(client):
    """Line 523: EN_to_IT con context != fantasy_rp → sistema generico."""
    with patch("app.calliope_shell.server.requests.post",
               return_value=_mock_gateway_response("Ciao.")):
        r = client.post("/api/translate", json={
            "text": "Hello.",
            "direction": "EN_to_IT",
            "context": "generic",
        })
    assert r.status_code == 200


def test_translate_missing_text(client):
    """Line 499: text mancante o vuoto → 400."""
    r = client.post("/api/translate", json={"direction": "IT_to_EN"})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_translate_gateway_timeout(client):
    """Lines 555-556: Timeout → 503."""
    import requests as req_module
    with patch("app.calliope_shell.server.requests.post",
               side_effect=req_module.exceptions.Timeout("timeout")):
        r = client.post("/api/translate", json={
            "text": "Ciao",
            "direction": "IT_to_EN",
        })
    assert r.status_code == 503
    assert "timeout" in r.get_json().get("error", "").lower()


def test_translate_generic_exception(client):
    """Lines 557-559: eccezione generica → 503."""
    with patch("app.calliope_shell.server.requests.post",
               side_effect=RuntimeError("unexpected")):
        r = client.post("/api/translate", json={
            "text": "Ciao",
            "direction": "IT_to_EN",
        })
    assert r.status_code == 503
    data = r.get_json()
    assert "error" in data


def test_translate_audit_exception_silenced(client):
    """Lines 550-551: audit_trail.log_event che lancia → silenziato, risposta ok."""
    with patch("app.calliope_shell.server.requests.post",
               return_value=_mock_gateway_response("Hello.")), \
         patch("app.calliope_shell.audit_trail.log_event", side_effect=RuntimeError("db")):
        r = client.post("/api/translate", json={
            "text": "Ciao.",
            "direction": "IT_to_EN",
        })
    assert r.status_code == 200
