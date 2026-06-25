"""
Test per route miscellanee di server.py non ancora coperte:
  POST /api/char/memory_replace         → validation 400 | requires_approval 202 | 200 | 400
  GET  /api/chars/<name>/memory         → chromadb fail (non-fatal fallback) | 200 con mock
  GET  /api/mascot/state                → 200 con ws_url
  POST /api/mascot/state                → aggiorna stato (requests.post mockato)
  GET  /api/mascot/emotion_map          → 200 con dict
  GET  /health                          → 200 {"status": "ok"}
  GET  /                                → 200 (ST vivo o giù, mocked)
  _load_emotion_map()                   → successo reale + fallback eccezione
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from app.calliope_shell.server import create_app

_SRV = "app.calliope_shell.server"


@pytest.fixture
def client():
    app, _ = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── POST /api/char/memory_replace ─────────────────────────────────────────────

def test_memory_replace_missing_fields_400(client):
    r = client.post("/api/char/memory_replace", json={"char": "Aurora"})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_memory_replace_requires_approval_202(client):
    mock_result = {"requires_approval": True, "diff": "old→new"}
    with patch(f"{_SRV}.char_memory_replace", return_value=mock_result):
        r = client.post("/api/char/memory_replace", json={
            "char": "Aurora", "old_fact": "Era timida", "new_fact": "È coraggiosa",
        })
    assert r.status_code == 202
    assert r.get_json()["requires_approval"] is True


def test_memory_replace_success_200(client):
    mock_result = {"success": True, "replaced": 1}
    with patch(f"{_SRV}.char_memory_replace", return_value=mock_result):
        r = client.post("/api/char/memory_replace", json={
            "char": "Aurora", "old_fact": "Era timida", "new_fact": "È coraggiosa",
            "approved": True,
        })
    assert r.status_code == 200
    assert r.get_json()["success"] is True


def test_memory_replace_failure_400(client):
    mock_result = {"success": False, "error": "fatto non trovato"}
    with patch(f"{_SRV}.char_memory_replace", return_value=mock_result):
        r = client.post("/api/char/memory_replace", json={
            "char": "Aurora", "old_fact": "Inesistente", "new_fact": "Nuovo",
            "approved": True,
        })
    assert r.status_code == 400


# ── GET /api/chars/<name>/memory ──────────────────────────────────────────────

def test_chars_memory_chromadb_fallback_on_error(client):
    """ChromaDB solleva eccezione → 200 con source=unavailable (non-fatal)."""
    with patch(f"{_SRV}._chroma_client", side_effect=Exception("chroma unavailable")):
        r = client.get("/api/chars/Aurora/memory")
    assert r.status_code == 200
    data = r.get_json()
    assert data["source"] == "unavailable"
    assert "error" in data


def test_chars_memory_with_results(client):
    mock_client = MagicMock()
    col = MagicMock()
    col.query.return_value = {
        "documents": [["Scena del drago", "Volo sulla torre"]],
        "distances": [[0.15, 0.22]],
    }
    mock_client.get_collection.return_value = col

    with patch(f"{_SRV}._chroma_client", return_value=mock_client):
        with patch(f"{_SRV}.get_char", return_value=None):
            r = client.get("/api/chars/Aurora/memory")

    assert r.status_code == 200
    data = r.get_json()
    assert data["source"] == "chromadb"
    assert len(data["snippets"]) == 2
    assert data["snippets"][0]["text"] == "Scena del drago"


# ── GET /api/mascot/state ─────────────────────────────────────────────────────

def test_mascot_state_get_200(client):
    r = client.get("/api/mascot/state")
    assert r.status_code == 200
    data = r.get_json()
    assert "emotion" in data
    assert "ws_url" in data


# ── POST /api/mascot/state ────────────────────────────────────────────────────

def test_mascot_state_post_ok(client):
    with patch(f"{_SRV}.requests.post") as mock_post:
        mock_post.return_value.raise_for_status = lambda: None
        r = client.post("/api/mascot/state", json={"emotion": "happy", "intensity": 0.8})
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ok"
    assert data["emotion"] == "happy"


def test_mascot_state_post_ws_fail_nonfatal(client):
    """requests.post fallisce → risposta 200 comunque (non-fatal)."""
    with patch(f"{_SRV}.requests.post", side_effect=Exception("connection refused")):
        r = client.post("/api/mascot/state", json={"emotion": "sad"})
    assert r.status_code == 200
    assert r.get_json()["emotion"] == "sad"


# ── GET /api/mascot/emotion_map ───────────────────────────────────────────────

def test_mascot_emotion_map_200(client):
    mock_map = {"happy": "smile", "sad": "tear", "neutral": "rest"}
    with patch(f"{_SRV}._load_emotion_map", return_value=mock_map):
        r = client.get("/api/mascot/emotion_map")
    assert r.status_code == 200
    data = r.get_json()
    assert "happy" in data


# ── GET /health (riga 226 server.py) ──────────────────────────────────────────

def test_health_200(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


# ── GET / index (righe 216-222 server.py) ─────────────────────────────────────

def test_index_200_st_down(client):
    """ST non raggiungibile → st_alive=False, ma pagina risponde 200."""
    with patch(f"{_SRV}.requests.head", side_effect=Exception("refused")):
        r = client.get("/")
    assert r.status_code == 200


def test_index_200_st_alive(client):
    """ST risponde 200 → st_alive=True, pagina risponde 200."""
    mock_head = MagicMock()
    mock_head.status_code = 200
    with patch(f"{_SRV}.requests.head", return_value=mock_head):
        r = client.get("/")
    assert r.status_code == 200


# ── _load_emotion_map() (righe 190-195 server.py) ─────────────────────────────

def test_load_emotion_map_real_file():
    """Il file data/calliope_emotion_map.yaml esiste: ritorna dict non vuoto."""
    from app.calliope_shell.server import _load_emotion_map
    result = _load_emotion_map()
    assert isinstance(result, dict)


def test_load_emotion_map_fallback_on_ioerror():
    """File non leggibile → except branch → ritorna {} senza sollevare."""
    from app.calliope_shell.server import _load_emotion_map
    with patch("pathlib.Path.read_text", side_effect=OSError("no file")):
        result = _load_emotion_map()
    assert result == {}
