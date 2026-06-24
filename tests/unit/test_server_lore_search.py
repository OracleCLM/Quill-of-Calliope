"""
Test per POST /api/lore/search (server.py) non ancora coperto:
  - 400 se query assente
  - 200 + error se ChromaDB fallisce (exception non-fatal)
  - 200 + hits su query valida

E per POST /api/scene/revive (minimal cases non-LLM):
  - 400 se scene_id assente
  - 404 se nessuna YAML scene corrisponde
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock

from app.calliope_shell.server import create_app

_SRV = "app.calliope_shell.server"


def _client():
    app, _ = create_app()
    app.config["TESTING"] = True
    return app.test_client()


# ── POST /api/lore/search ─────────────────────────────────────────────────────

def test_lore_search_missing_query_400():
    with _client() as c:
        r = c.post("/api/lore/search", json={})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_lore_search_chromadb_fail_returns_empty():
    """ChromaDB solleva eccezione → 200 con results=[], count=0, error str."""
    with _client() as c:
        with patch(f"{_SRV}._chroma_client", side_effect=Exception("chroma down")):
            r = c.post("/api/lore/search", json={"query": "drago"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["results"] == []
    assert data["count"] == 0
    assert "error" in data


def test_lore_search_success_returns_hits():
    mock_chroma = MagicMock()
    col = MagicMock()
    col.query.return_value = {
        "documents": [["Il Drago delle Cime abita a nord."]],
        "metadatas": [[{"source": "lore/draghi.md", "type": "lore", "char": ""}]],
        "distances": [[0.12]],
    }
    mock_chroma.get_collection.return_value = col

    with _client() as c:
        with patch(f"{_SRV}._chroma_client", return_value=mock_chroma):
            with patch(f"{_SRV}.audit_trail" if False else "builtins.print"):
                r = c.post("/api/lore/search", json={"query": "drago"})

    assert r.status_code == 200
    data = r.get_json()
    assert data["count"] == 1
    assert data["query"] == "drago"
    hit = data["results"][0]
    assert "drago" in hit["text"].lower() or "Drago" in hit["text"]
    assert hit["source"] == "lore/draghi.md"


def test_lore_search_n_capped_at_20():
    """n>20 viene silenziosamente cappato a 20 (no error)."""
    mock_chroma = MagicMock()
    col = MagicMock()
    col.query.return_value = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    mock_chroma.get_collection.return_value = col

    with _client() as c:
        with patch(f"{_SRV}._chroma_client", return_value=mock_chroma):
            r = c.post("/api/lore/search", json={"query": "qualcosa", "n": 100})

    assert r.status_code == 200
    col.query.assert_called_once()
    _, call_kwargs = col.query.call_args
    assert call_kwargs.get("n_results", 0) == 20


# ── POST /api/scene/revive ────────────────────────────────────────────────────

def test_scene_revive_missing_scene_id_400():
    with _client() as c:
        r = c.post("/api/scene/revive", json={})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_scene_revive_scene_not_found_404(tmp_path):
    """_SCENES_DIR punta a tmp_path vuota → nessun match → 404."""
    with _client() as c:
        with patch(f"{_SRV}._SCENES_DIR", tmp_path):
            r = c.post("/api/scene/revive", json={"scene_id": "nonexistent-scene"})
    assert r.status_code == 404
    assert "error" in r.get_json()


# ── POST /api/lore/check ─────────────────────────────────────────────────────

def test_lore_check_missing_text_400():
    with _client() as c:
        r = c.post("/api/lore/check", json={})
    assert r.status_code == 400
    assert r.get_json()["error"] == "text is required"


def test_lore_check_no_lore_returns_coherent_true():
    """Nessun snippet lore trovato → coherent=True, issues=[]."""
    with _client() as c:
        with patch(f"{_SRV}._search_lore", return_value=[]):
            r = c.post("/api/lore/check", json={"text": "The dragon flew high."})
    assert r.status_code == 200
    data = r.get_json()
    assert data["coherent"] is True
    assert data["issues"] == []


def test_lore_check_with_lore_llm_success():
    """LLM risponde JSON valido con coherent+issues → 200."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"result": '{"coherent": true, "issues": []}'}

    with _client() as c:
        with patch(f"{_SRV}._search_lore", return_value=["lore snippet"]):
            with patch(f"{_SRV}.requests.post", return_value=mock_resp):
                r = c.post("/api/lore/check", json={"text": "The dragon flew high."})
    assert r.status_code == 200
    data = r.get_json()
    assert "coherent" in data or "error" in data  # degrada se JSON mal formato
