"""
Test per POST /api/translate (server.py) non ancora coperti:
  - 400 se text assente
  - 400 se direction invalida
  - 200 con traduzione mock (requests.post mockato)
  - 503 su ConnectionError gateway
  - 503 su Timeout gateway
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import requests as req_mod

from app.calliope_shell.server import create_app

_SRV = "app.calliope_shell.server"


def _client():
    app, _ = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _mock_translate_response(text: str):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {"result": text}
    return mock_resp


# ── Validazione ───────────────────────────────────────────────────────────────

def test_translate_missing_text_400():
    with _client() as c:
        r = c.post("/api/translate", json={"direction": "IT_to_EN"})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_translate_invalid_direction_400():
    with _client() as c:
        r = c.post("/api/translate", json={"text": "Ciao", "direction": "XY_to_ZZ"})
    assert r.status_code == 400
    assert "error" in r.get_json()


# ── Successo (LLM mockato) ────────────────────────────────────────────────────

def test_translate_it_to_en_success():
    with _client() as c:
        with patch(f"{_SRV}.requests.post", return_value=_mock_translate_response("Hello world")):
            r = c.post("/api/translate", json={"text": "Ciao mondo", "direction": "IT_to_EN"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["translation"] == "Hello world"
    assert "model_used" in data


def test_translate_en_to_it_success():
    with _client() as c:
        with patch(f"{_SRV}.requests.post", return_value=_mock_translate_response("Ciao mondo")):
            r = c.post("/api/translate", json={"text": "Hello world", "direction": "EN_to_IT"})
    assert r.status_code == 200
    assert r.get_json()["translation"] == "Ciao mondo"


# ── Errori gateway ────────────────────────────────────────────────────────────

def test_translate_gateway_connection_error_503():
    with _client() as c:
        with patch(f"{_SRV}.requests.post", side_effect=req_mod.exceptions.ConnectionError("down")):
            r = c.post("/api/translate", json={"text": "Ciao", "direction": "IT_to_EN"})
    assert r.status_code == 503
    assert "gateway" in r.get_json().get("error", "").lower()


def test_translate_gateway_timeout_503():
    with _client() as c:
        with patch(f"{_SRV}.requests.post", side_effect=req_mod.exceptions.Timeout("slow")):
            r = c.post("/api/translate", json={"text": "Ciao", "direction": "IT_to_EN"})
    assert r.status_code == 503
