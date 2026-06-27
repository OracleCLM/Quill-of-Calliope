"""GAP-77: test per /api/summarize e /api/lore/check in server.py."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import requests as _req

from app.calliope_shell.server import create_app


@pytest.fixture
def client():
    app, _ = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _mock_ok(text="risposta"):
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"result": text}
    mock.raise_for_status = MagicMock()
    return mock


# ── POST /api/summarize ───────────────────────────────────────────────────────


def test_summarize_missing_text_returns_400(client):
    r = client.post("/api/summarize", json={})
    assert r.status_code == 400


def test_summarize_empty_text_returns_400(client):
    r = client.post("/api/summarize", json={"text": ""})
    assert r.status_code == 400


def test_summarize_gateway_down_returns_503(client):
    with patch("requests.post", side_effect=_req.exceptions.ConnectionError):
        r = client.post("/api/summarize", json={"text": "testo da riassumere"})
    assert r.status_code == 503


def test_summarize_ok_returns_summary_and_key_facts(client):
    json_resp = '{"summary": "Breve riassunto.", "key_facts": ["fatto"]}'
    with patch("requests.post", return_value=_mock_ok(json_resp)):
        r = client.post("/api/summarize", json={"text": "testo lungo"})
    assert r.status_code == 200
    data = r.get_json()
    assert "summary" in data
    assert "key_facts" in data
    assert "word_count" in data


def test_summarize_raw_text_fallback(client):
    with patch("requests.post", return_value=_mock_ok("testo grezzo")):
        r = client.post("/api/summarize", json={"text": "testo"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["summary"] == "testo grezzo"


# ── POST /api/lore/check ──────────────────────────────────────────────────────


def test_lore_check_missing_text_returns_400(client):
    r = client.post("/api/lore/check", json={})
    assert r.status_code == 400


def test_lore_check_graceful_without_chromadb(client):
    with patch("app.calliope_shell.server._search_lore", return_value=[]):
        r = client.post("/api/lore/check", json={"text": "testo di prova"})
    assert r.status_code == 200


def test_lore_check_no_lore_returns_coherent_true(client):
    with patch("app.calliope_shell.server._search_lore", return_value=[]):
        data = client.post("/api/lore/check", json={"text": "testo"}).get_json()
    assert data["coherent"] is True
    assert "issues" in data
