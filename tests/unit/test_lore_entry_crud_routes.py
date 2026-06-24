"""
Test per gli endpoint lore non ancora coperti:
  GET  /api/lore/entries/<id>       → 200 | 404
  POST /api/lore/entries            → 201 | 400
  DELETE /api/lore/entries/<id>     → 200 | 404
"""
from __future__ import annotations

import pytest
from flask import Flask

from app.calliope_shell.lore_routes import register_lore_routes


@pytest.fixture
def client(tmp_path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_lore_routes(app, store_path=tmp_path / "lore.json")
    return app.test_client()


def _create(client, title="Aetheron", category="places", content="Descrizione."):
    r = client.post("/api/lore/entries", json={
        "title": title, "category": category, "content": content,
    })
    assert r.status_code == 201
    return r.get_json()["id"]


# ── POST /api/lore/entries ────────────────────────────────────────────────────

def test_post_lore_entry_201(client):
    r = client.post("/api/lore/entries", json={"title": "Lago Nero", "category": "places"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["title"] == "Lago Nero"
    assert "id" in data


def test_post_lore_entry_missing_title_400(client):
    r = client.post("/api/lore/entries", json={"category": "places"})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_post_lore_entry_empty_title_400(client):
    r = client.post("/api/lore/entries", json={"title": "   "})
    assert r.status_code == 400


def test_post_lore_entry_defaults(client):
    r = client.post("/api/lore/entries", json={"title": "Entità anonima"})
    data = r.get_json()
    assert r.status_code == 201
    assert data.get("category") == "other"
    assert isinstance(data.get("insertion_order"), int)


def test_post_lore_entry_custom_fields(client):
    r = client.post("/api/lore/entries", json={
        "title": "Voce importante",
        "category": "events",
        "keys": ["battaglia", "aurora"],
        "insertion_order": 50,
        "constant": True,
    })
    data = r.get_json()
    assert r.status_code == 201
    assert data["insertion_order"] == 50
    assert data["constant"] is True
    assert "battaglia" in data["keys"]


# ── GET /api/lore/entries/<id> ────────────────────────────────────────────────

def test_get_lore_entry_by_id_200(client):
    eid = _create(client, "Torre dell'Est")
    r = client.get(f"/api/lore/entries/{eid}")
    assert r.status_code == 200
    data = r.get_json()
    assert data["id"] == eid
    assert data["title"] == "Torre dell'Est"


def test_get_lore_entry_not_found_404(client):
    r = client.get("/api/lore/entries/entry-inesistente")
    assert r.status_code == 404
    assert "error" in r.get_json()


def test_get_lore_entry_returns_full_dict(client):
    eid = _create(client, "Rovina", category="places", content="Un luogo antico.")
    data = client.get(f"/api/lore/entries/{eid}").get_json()
    assert data["category"] == "places"
    assert data["content"] == "Un luogo antico."


# ── DELETE /api/lore/entries/<id> ─────────────────────────────────────────────

def test_delete_lore_entry_200(client):
    eid = _create(client, "Da eliminare")
    r = client.delete(f"/api/lore/entries/{eid}")
    assert r.status_code == 200
    assert r.get_json().get("deleted") is True


def test_delete_lore_entry_not_found_404(client):
    r = client.delete("/api/lore/entries/nonexistent-id")
    assert r.status_code == 404
    assert "error" in r.get_json()


def test_delete_lore_entry_then_get_404(client):
    eid = _create(client, "Temporanea")
    client.delete(f"/api/lore/entries/{eid}")
    r = client.get(f"/api/lore/entries/{eid}")
    assert r.status_code == 404


def test_post_lore_entry_bad_insertion_order_uses_default(client):
    r = client.post("/api/lore/entries", json={"title": "T", "insertion_order": "bad"})
    assert r.status_code == 201
    assert isinstance(r.get_json()["insertion_order"], int)
