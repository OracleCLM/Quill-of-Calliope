"""GAP-73: test response shape dei verbi write — genera/rifinisci/coerenza/traduci/riassumi."""

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


def _mock_ok(text="risposta mock"):
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"result": text}
    mock.raise_for_status = MagicMock()
    return mock


# ── genera ────────────────────────────────────────────────────────────────────


def test_genera_response_has_draft_text(client):
    with patch("requests.post", return_value=_mock_ok("bozza scena")):
        r = client.post("/api/write", json={"action": "genera", "intent_it": "apri la scena"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["action"] == "genera"
    assert data["draft_text"] == "bozza scena"


# ── rifinisci ─────────────────────────────────────────────────────────────────


def test_rifinisci_response_has_refined_text(client):
    with patch("requests.post", return_value=_mock_ok("testo rifinito")):
        r = client.post("/api/write", json={"action": "rifinisci", "text": "testo grezzo"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["action"] == "rifinisci"
    assert "refined_text" in data
    assert data["refined_text"] == "testo rifinito"


# ── coerenza ──────────────────────────────────────────────────────────────────


def test_coerenza_response_has_coherent_and_issues(client):
    ok_json = '{"coherent": true, "issues": []}'
    with patch("requests.post", return_value=_mock_ok(ok_json)):
        r = client.post("/api/write", json={"action": "coerenza", "text": "testo da verificare"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["action"] == "coerenza"
    assert "coherent" in data
    assert "issues" in data


def test_coerenza_json_parse_failure_graceful(client):
    with patch("requests.post", return_value=_mock_ok("INVALID JSON !!!")):
        r = client.post("/api/write", json={"action": "coerenza", "text": "testo da verificare"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["coherent"] is False
    assert len(data["issues"]) >= 1


# ── traduci ───────────────────────────────────────────────────────────────────


def test_traduci_response_has_translation(client):
    with patch("requests.post", return_value=_mock_ok("translated text")):
        r = client.post("/api/write", json={"action": "traduci", "text": "ciao mondo"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["action"] == "traduci"
    assert data["translation"] == "translated text"


def test_traduci_en_to_it_accepted(client):
    with patch("requests.post", return_value=_mock_ok("testo tradotto")):
        r = client.post("/api/write", json={
            "action": "traduci", "text": "hello world", "direction": "EN_to_IT"
        })
    assert r.status_code == 200


# ── riassumi ──────────────────────────────────────────────────────────────────


def test_riassumi_response_has_summary_and_key_facts(client):
    json_resp = '{"summary": "Un riassunto.", "key_facts": ["fatto 1"]}'
    with patch("requests.post", return_value=_mock_ok(json_resp)):
        r = client.post("/api/write", json={"action": "riassumi", "text": "testo lungo da riassumere"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["action"] == "riassumi"
    assert "summary" in data
    assert "key_facts" in data


def test_riassumi_json_parse_failure_returns_raw_text(client):
    with patch("requests.post", return_value=_mock_ok("testo grezzo non JSON")):
        r = client.post("/api/write", json={"action": "riassumi", "text": "testo"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["summary"] == "testo grezzo non JSON"
    assert data["key_facts"] == []
