"""GAP-29: test contratto per POST /api/lore/search — zero test esistenti."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def _make_app():
    from app.calliope_shell.server import create_app
    app, _ = create_app()
    app.config["TESTING"] = True
    return app


def _mock_chroma(docs=None, metas=None, dists=None):
    docs = docs or ["documento lore"]
    metas = metas or [{"source": "wiki.md", "type": "world", "char": ""}]
    dists = dists or [0.12]
    col = MagicMock()
    col.query.return_value = {
        "documents": [docs],
        "metadatas": [metas],
        "distances": [dists],
    }
    client = MagicMock()
    client.get_collection.return_value = col
    return client


# --- validazione input -------------------------------------------------------


def test_lore_search_missing_query_returns_400():
    app = _make_app()
    with app.test_client() as c:
        r = c.post("/api/lore/search", json={})
    assert r.status_code == 400
    assert "query" in r.get_json()["error"]


def test_lore_search_empty_query_returns_400():
    app = _make_app()
    with app.test_client() as c:
        r = c.post("/api/lore/search", json={"query": "   "})
    assert r.status_code == 400


# --- risposta con risultati --------------------------------------------------


def test_lore_search_returns_hits_list():
    with patch("app.calliope_shell.server._chroma_client", return_value=_mock_chroma()):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/lore/search", json={"query": "drago"})
    assert r.status_code == 200
    data = r.get_json()
    assert "results" in data
    assert data["count"] == 1
    assert data["query"] == "drago"


def test_lore_search_hit_shape():
    with patch("app.calliope_shell.server._chroma_client", return_value=_mock_chroma()):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/lore/search", json={"query": "tempio"})
    hit = r.get_json()["results"][0]
    for key in ("text", "source", "type", "char", "distance"):
        assert key in hit


def test_lore_search_n_cap_at_20():
    docs = ["doc"] * 25
    metas = [{"source": "", "type": "", "char": ""}] * 25
    dists = [0.1] * 25
    mock = _mock_chroma(docs=docs, metas=metas, dists=dists)
    with patch("app.calliope_shell.server._chroma_client", return_value=mock):
        app = _make_app()
        with app.test_client() as c:
            c.post("/api/lore/search", json={"query": "qualcosa", "n": 100})
    _, kwargs = mock.get_collection.return_value.query.call_args
    assert kwargs.get("n_results", 0) <= 20


# --- fallback su errore ChromaDB --------------------------------------------


def test_lore_search_chroma_error_returns_empty_results():
    broken = MagicMock()
    broken.get_collection.side_effect = RuntimeError("chroma down")
    with patch("app.calliope_shell.server._chroma_client", return_value=broken):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/lore/search", json={"query": "test"})
    data = r.get_json()
    assert data["results"] == []
    assert data["count"] == 0
    assert "error" in data
