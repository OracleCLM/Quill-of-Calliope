"""GAP-40: fix(write_routes): max_length non-numerico e JSON-parse fallback per riassumi/coerenza."""

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


def _mock_resp(text):
    mock = MagicMock()
    mock.status_code = 200
    mock.ok = True
    mock.json.return_value = {"result": text}
    mock.raise_for_status = MagicMock()
    return mock


# ── riassumi — max_length non-numerico ───────────────────────────────────────


def test_riassumi_max_length_string_no_crash(client):
    """Bug fix: int(body.get("max_length")) crashed con input non-numerico."""
    with patch("requests.post", return_value=_mock_resp('{"summary":"S","key_facts":[]}')):
        r = client.post("/api/write", json={
            "action": "riassumi",
            "text": "testo di prova",
            "max_length": "non-un-numero",
        })
    assert r.status_code == 200


def test_riassumi_max_length_zero_no_crash(client):
    with patch("requests.post", return_value=_mock_resp('{"summary":"S","key_facts":[]}')):
        r = client.post("/api/write", json={
            "action": "riassumi",
            "text": "testo",
            "max_length": 0,
        })
    assert r.status_code == 200


def test_riassumi_max_length_capped_at_500(client):
    with patch("requests.post", return_value=_mock_resp('{"summary":"S","key_facts":[]}')) as mock_req:
        r = client.post("/api/write", json={
            "action": "riassumi",
            "text": "testo",
            "max_length": 9999,
        })
    assert r.status_code == 200
    # il prompt deve contenere "max 500 words" (o <= 500)
    call_payload = mock_req.call_args[1]["json"]
    prompt = call_payload.get("prompt", "")
    assert "500" in prompt


# ── riassumi — JSON parse fallback ───────────────────────────────────────────


def test_riassumi_plain_text_fallback(client):
    """LLM restituisce testo non-JSON: summary=testo grezzo, key_facts=[]."""
    with patch("requests.post", return_value=_mock_resp("Questo è un riassunto in prosa.")):
        r = client.post("/api/write", json={"action": "riassumi", "text": "testo"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["summary"] == "Questo è un riassunto in prosa."
    assert body["key_facts"] == []


def test_riassumi_json_with_markdown_fence_parsed(client):
    """LLM avvolge il JSON in ```json ... ``` → deve essere parsato correttamente."""
    response_text = '```json\n{"summary": "Il castello cadde", "key_facts": ["fatto1"]}\n```'
    with patch("requests.post", return_value=_mock_resp(response_text)):
        r = client.post("/api/write", json={"action": "riassumi", "text": "testo"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["summary"] == "Il castello cadde"
    assert body["key_facts"] == ["fatto1"]


def test_riassumi_valid_json_parsed(client):
    """LLM restituisce JSON valido: summary e key_facts estratti."""
    response_text = '{"summary": "Riassunto breve", "key_facts": ["a", "b"]}'
    with patch("requests.post", return_value=_mock_resp(response_text)):
        r = client.post("/api/write", json={"action": "riassumi", "text": "testo"})
    body = r.get_json()
    assert body["summary"] == "Riassunto breve"
    assert "a" in body["key_facts"]


# ── coerenza — JSON parse fallback ───────────────────────────────────────────


def test_coerenza_plain_text_fallback(client):
    """LLM restituisce testo non-JSON: coherent=False, issues=[parse-failed]."""
    with patch("requests.post", return_value=_mock_resp("Non posso rispondere in JSON.")):
        r = client.post("/api/write", json={"action": "coerenza", "text": "testo"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["coherent"] is False
    assert len(body["issues"]) >= 1
    assert any("parse" in str(i).lower() for i in body["issues"])


def test_coerenza_valid_json_coherent_true(client):
    response_text = '{"coherent": true, "issues": []}'
    with patch("requests.post", return_value=_mock_resp(response_text)):
        r = client.post("/api/write", json={"action": "coerenza", "text": "testo coerente"})
    body = r.get_json()
    assert body["coherent"] is True
    assert body["issues"] == []


def test_coerenza_valid_json_with_issues(client):
    response_text = '{"coherent": false, "issues": [{"severity": "high", "description": "errore lore"}]}'
    with patch("requests.post", return_value=_mock_resp(response_text)):
        r = client.post("/api/write", json={"action": "coerenza", "text": "testo"})
    body = r.get_json()
    assert body["coherent"] is False
    assert len(body["issues"]) == 1


def test_coerenza_json_fence_parsed(client):
    response_text = '```\n{"coherent": true, "issues": []}\n```'
    with patch("requests.post", return_value=_mock_resp(response_text)):
        r = client.post("/api/write", json={"action": "coerenza", "text": "testo"})
    body = r.get_json()
    assert body["coherent"] is True


# ── gateway down ─────────────────────────────────────────────────────────────


def test_riassumi_gateway_down_returns_503(client):
    import requests as _requests
    with patch("requests.post", side_effect=_requests.exceptions.ConnectionError):
        r = client.post("/api/write", json={"action": "riassumi", "text": "testo"})
    assert r.status_code == 503
    assert "gateway" in r.get_json()["error"].lower()
