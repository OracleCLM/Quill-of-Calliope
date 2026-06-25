"""Unit test per POST /api/scene/refine, /api/scene/variants, /api/draft, /api/summarize."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.calliope_shell.server import create_app

_SRV = "app.calliope_shell.server"
_SCRIPTS = str(Path(__file__).parents[2] / "scripts")


def _client():
    app, _ = create_app()
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def client():
    return _client()


@pytest.fixture(autouse=True)
def add_scripts_to_path():
    sys.path.insert(0, _SCRIPTS)
    yield
    if _SCRIPTS in sys.path:
        sys.path.remove(_SCRIPTS)


# ── POST /api/scene/refine ────────────────────────────────────────────────────

def test_refine_400_no_input(client):
    r = client.post("/api/scene/refine", json={})
    assert r.status_code == 400


def test_refine_400_no_feedback(client):
    r = client.post("/api/scene/refine", json={"scene_text": "old text"})
    assert r.status_code == 400


def test_refine_503_llm_error(client):
    with patch(f"{_SRV}.requests.post", side_effect=Exception("LLM unavailable")):
        r = client.post("/api/scene/refine", json={"scene_text": "text", "feedback": "fix it"})
    assert r.status_code == 503


def test_refine_200_success(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"result": "refined text here"}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp):
        r = client.post("/api/scene/refine", json={"scene_text": "original", "feedback": "shorter"})
    assert r.status_code == 200
    data = r.get_json()
    assert "refined_text" in data
    assert "diff" in data


# ── POST /api/scene/variants ──────────────────────────────────────────────────

def test_variants_400_no_prompt(client):
    r = client.post("/api/scene/variants", json={})
    assert r.status_code == 400


def test_variants_503_generation_error(client):
    with patch("generate_scene.generate_variants", side_effect=RuntimeError("gen failed")):
        r = client.post("/api/scene/variants", json={"prompt": "a battle"})
    assert r.status_code == 503


# ── POST /api/draft ───────────────────────────────────────────────────────────

def test_draft_400_no_intent(client):
    r = client.post("/api/draft", json={})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_draft_400_empty_intent(client):
    r = client.post("/api/draft", json={"intent_it": "   "})
    assert r.status_code == 400


# ── POST /api/summarize ───────────────────────────────────────────────────────

def test_summarize_400_no_text(client):
    r = client.post("/api/summarize", json={})
    assert r.status_code == 400


def test_summarize_503_connection_error(client):
    with patch(f"{_SRV}.requests.post", side_effect=requests.exceptions.ConnectionError):
        r = client.post("/api/summarize", json={"text": "some text to summarize"})
    assert r.status_code == 503


def test_summarize_200_success(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"result": '{"summary": "short", "key_facts": ["a", "b"]}'}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp):
        r = client.post("/api/summarize", json={"text": "long scene text here"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["summary"] == "short"
    assert data["key_facts"] == ["a", "b"]
    assert "word_count" in data


# ── POST /api/scene/blend ─────────────────────────────────────────────────────

def test_scene_blend_400_missing_variants_file(client):
    """Lines 831-832: variants_file_path mancante → 400."""
    r = client.post("/api/scene/blend", json={})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_scene_blend_400_path_traversal(client):
    """Lines 834-835: path fuori da /tmp o scenes/ → 400."""
    r = client.post("/api/scene/blend", json={"variants_file_path": "/etc/calliope_x.variants.md"})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_scene_blend_404_file_not_found(client):
    """Lines 836-837: path valido ma file inesistente → 404."""
    r = client.post("/api/scene/blend", json={
        "variants_file_path": "/tmp/calliope_nonexistent_test.variants.md",
    })
    assert r.status_code == 404
    assert "error" in r.get_json()


# ── Extra /api/summarize branches ────────────────────────────────────────────

def test_summarize_codeblock_json(client):
    """Line 1295: risposta LLM con JSON dentro code-block markdown."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "result": '```json\n{"summary": "short", "key_facts": ["x"]}\n```',
    }
    with patch(f"{_SRV}.requests.post", return_value=mock_resp):
        r = client.post("/api/summarize", json={"text": "some long text"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["summary"] == "short"


def test_summarize_non_json_result(client):
    """Lines 1299-1300: risposta LLM non JSON → summary = testo grezzo."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"result": "plain text, no JSON here"}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp):
        r = client.post("/api/summarize", json={"text": "text"})
    assert r.status_code == 200
    assert r.get_json()["summary"] == "plain text, no JSON here"


def test_summarize_generic_llm_exception(client):
    """Lines 1285-1287: eccezione generica nell'LLM call → 503."""
    with patch(f"{_SRV}.requests.post", side_effect=RuntimeError("oops")):
        r = client.post("/api/summarize", json={"text": "text"})
    assert r.status_code == 503


def test_summarize_audit_exception_silenced(client):
    """Lines 1310-1311: audit_trail.log_event lancia → silenziato."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"result": '{"summary": "s", "key_facts": []}'}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp), \
         patch("app.calliope_shell.audit_trail.log_event", side_effect=RuntimeError("db")):
        r = client.post("/api/summarize", json={"text": "text"})
    assert r.status_code == 200
