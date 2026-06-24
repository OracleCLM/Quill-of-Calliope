"""
Test per gli endpoint char-memory di server.py, non ancora coperti:
  GET  /api/chars              → list_chars()
  POST /api/chars              → upsert_char() + validation
  GET  /api/chars/<name>       → get_char() (200/404)
  POST /api/char/memory_append → char_memory_append (200/400)
  POST /api/char/recall        → char_memory_recall (200/400)
  GET  /api/char/<name>/facts  → char_memory_list_facts (200)

Tutti mockano le funzioni sottostanti per evitare dipendenza da char_memory.db.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch

from app.calliope_shell.server import create_app

_SRV = "app.calliope_shell.server"


@pytest.fixture
def client():
    app, _ = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── GET /api/chars ────────────────────────────────────────────────────────────

def test_chars_list_empty(client):
    with patch(f"{_SRV}.list_chars", return_value=[]):
        r = client.get("/api/chars")
    assert r.status_code == 200
    assert r.get_json() == []


def test_chars_list_with_chars(client):
    chars = [
        {"name": "Aurora", "traits_summary": "strega", "updated_at": "2026-01-01"},
    ]
    with patch(f"{_SRV}.list_chars", return_value=chars):
        r = client.get("/api/chars")
    data = r.get_json()
    assert isinstance(data, list)
    assert data[0]["name"] == "Aurora"


# ── POST /api/chars ───────────────────────────────────────────────────────────

def test_chars_upsert_success(client):
    with patch(f"{_SRV}.upsert_char") as mock_upsert:
        r = client.post("/api/chars", json={"name": "Luna"})
    assert r.status_code == 200
    assert r.get_json()["name"] == "Luna"
    mock_upsert.assert_called_once()


def test_chars_upsert_missing_name_400(client):
    r = client.post("/api/chars", json={"traits": "qualcosa"})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_chars_upsert_empty_name_400(client):
    r = client.post("/api/chars", json={"name": "  "})
    assert r.status_code == 400


# ── GET /api/chars/<name> ─────────────────────────────────────────────────────

def test_chars_get_found(client):
    char = {"name": "Aurora", "traits_summary": "coraggiosa"}
    with patch(f"{_SRV}.get_char", return_value=char):
        r = client.get("/api/chars/Aurora")
    assert r.status_code == 200
    assert r.get_json()["name"] == "Aurora"


def test_chars_get_not_found_404(client):
    with patch(f"{_SRV}.get_char", return_value=None):
        r = client.get("/api/chars/Fantasma")
    assert r.status_code == 404
    assert "error" in r.get_json()


# ── POST /api/char/memory_append ──────────────────────────────────────────────

def test_char_memory_append_success(client):
    mock_result = {"success": True, "fact_id": "abc", "scope": "L1", "fact_preview": "x"}
    with patch(f"{_SRV}.char_memory_append", return_value=mock_result):
        r = client.post("/api/char/memory_append", json={"char": "Aurora", "fact": "Ha ucciso il drago"})
    assert r.status_code == 200
    assert r.get_json()["success"] is True


def test_char_memory_append_missing_char_400(client):
    r = client.post("/api/char/memory_append", json={"fact": "qualcosa"})
    assert r.status_code == 400


def test_char_memory_append_missing_fact_400(client):
    r = client.post("/api/char/memory_append", json={"char": "Aurora"})
    assert r.status_code == 400


def test_char_memory_append_failure_returns_400(client):
    mock_result = {"success": False, "error": "DB error"}
    with patch(f"{_SRV}.char_memory_append", return_value=mock_result):
        r = client.post("/api/char/memory_append", json={"char": "Aurora", "fact": "fatto"})
    assert r.status_code == 400


# ── POST /api/char/recall ─────────────────────────────────────────────────────

def test_char_recall_success(client):
    mock_result = {"success": True, "results": []}
    with patch(f"{_SRV}.char_memory_recall", return_value=mock_result):
        r = client.post("/api/char/recall", json={"char": "Aurora", "query": "drago"})
    assert r.status_code == 200
    assert r.get_json()["success"] is True


def test_char_recall_missing_char_400(client):
    r = client.post("/api/char/recall", json={"query": "drago"})
    assert r.status_code == 400


def test_char_recall_missing_query_400(client):
    r = client.post("/api/char/recall", json={"char": "Aurora"})
    assert r.status_code == 400


# ── GET /api/char/<name>/facts ────────────────────────────────────────────────

def test_char_facts_list_200(client):
    mock_result = {"facts": [{"scope": "L1", "fact_text": "Cavalca un drago"}]}
    with patch(f"{_SRV}.char_memory_list_facts", return_value=mock_result):
        r = client.get("/api/char/Aurora/facts")
    assert r.status_code == 200
    assert "facts" in r.get_json()


def test_char_facts_list_empty(client):
    with patch(f"{_SRV}.char_memory_list_facts", return_value={"facts": []}):
        r = client.get("/api/char/Ghost/facts")
    assert r.status_code == 200
    assert r.get_json()["facts"] == []
