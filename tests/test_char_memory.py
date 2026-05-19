"""Sprint-C tests: char_memory SQLite + /api/chars routes."""
from __future__ import annotations
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import app.calliope_shell.char_memory as cm
from app.calliope_shell.server import create_app


# ── SQLite tests ──────────────────────────────────────────────────────────────

def test_upsert_get(tmp_path):
    """Insert char, retrieve it, assert fields."""
    orig_path = cm._DB_PATH
    try:
        cm._DB_PATH = tmp_path / "test_char_memory.db"
        cm.init_db()
        cm.upsert_char(
            name="Philly",
            traits={"personality": ["brave", "impulsive"], "quirks": [], "flaws": ["reckless"]},
            last_action="entered the tavern",
            relationships={"Aurora": "ally"},
            last_scene_id="scene_007",
        )
        char = cm.get_char("Philly")
        assert char is not None
        assert char["name"] == "Philly"
        assert char["traits"]["personality"] == ["brave", "impulsive"]
        assert char["relationships"]["Aurora"] == "ally"
        assert char["last_scene_id"] == "scene_007"
    finally:
        cm._DB_PATH = orig_path
        cm.init_db()


def test_chromadb_recall(client_with_mock_chroma):
    """Mock ChromaDB query returns top-5 snippets for char name."""
    r = client_with_mock_chroma.get("/api/chars/Aurora/memory")
    assert r.status_code == 200
    data = r.get_json()
    assert "snippets" in data
    assert len(data["snippets"]) <= 5


def test_api_chars_list(flask_client):
    """GET /api/chars returns a list."""
    r = flask_client.get("/api/chars")
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, list)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def flask_client():
    app, _ = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture()
def client_with_mock_chroma():
    mock_col = MagicMock()
    mock_col.query.return_value = {
        "documents": [["Aurora spoke softly.", "The queen raised her hand.", "She smiled."]],
        "distances": [[0.12, 0.23, 0.34]],
    }
    mock_client = MagicMock()
    mock_client.get_collection.return_value = mock_col

    app, _ = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        with patch("app.calliope_shell.server._chroma_client", return_value=mock_client):
            yield c
