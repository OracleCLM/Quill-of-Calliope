"""GAP-49: test per POST /api/lore/entries — validazione e struttura risposta."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from flask import Flask

from app.calliope_shell.lore_routes import register_lore_routes


@pytest.fixture
def client(tmp_path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_lore_routes(app, store_path=tmp_path / "lore.json")
    return app.test_client()


# ── POST /api/lore/entries ────────────────────────────────────────────────────


def test_create_returns_201(client):
    r = client.post("/api/lore/entries", json={"title": "Midgard"})
    assert r.status_code == 201


def test_create_missing_title_returns_400(client):
    r = client.post("/api/lore/entries", json={"category": "places"})
    assert r.status_code == 400


def test_create_empty_title_returns_400(client):
    r = client.post("/api/lore/entries", json={"title": "  "})
    assert r.status_code == 400


def test_create_returns_id(client):
    data = client.post("/api/lore/entries", json={"title": "Yggdrasil"}).get_json()
    assert "id" in data and data["id"]


def test_create_title_stored(client):
    data = client.post("/api/lore/entries", json={"title": "Asgard"}).get_json()
    assert data["title"] == "Asgard"


def test_create_category_stored(client):
    data = client.post(
        "/api/lore/entries", json={"title": "Foresta", "category": "places"}
    ).get_json()
    assert data["category"] == "places"


def test_create_content_stored(client):
    data = client.post(
        "/api/lore/entries", json={"title": "X", "content": "Contenuto magico"}
    ).get_json()
    assert data["content"] == "Contenuto magico"


def test_create_keys_stored(client):
    data = client.post(
        "/api/lore/entries", json={"title": "X", "keys": ["drago", "dragon"]}
    ).get_json()
    assert "drago" in data["keys"]


def test_create_constant_stored(client):
    data = client.post(
        "/api/lore/entries", json={"title": "X", "constant": True}
    ).get_json()
    assert data["constant"] is True


def test_create_insertion_order_non_int_uses_fallback(client):
    data = client.post(
        "/api/lore/entries", json={"title": "X", "insertion_order": "non-int"}
    ).get_json()
    assert isinstance(data["insertion_order"], int)


def test_create_multiple_entries_unique_ids(client):
    id1 = client.post("/api/lore/entries", json={"title": "A"}).get_json()["id"]
    id2 = client.post("/api/lore/entries", json={"title": "B"}).get_json()["id"]
    assert id1 != id2


def test_create_appears_in_list(client):
    client.post("/api/lore/entries", json={"title": "Midgard"})
    r = client.get("/api/lore/entries")
    assert r.status_code == 200
    titles = [e["title"] for e in r.get_json()["entries"]]
    assert "Midgard" in titles
