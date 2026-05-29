import pytest

from app.calliope_shell import lore_kb
from app.calliope_shell.server import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Hermetic: redirect the lore KB store to a temp file so tests never touch
    # the real data/lore_kb.json. LoreStore() with no path uses _default_store_path().
    store_file = tmp_path / "lore_kb.json"
    monkeypatch.setattr(lore_kb, "_default_store_path", lambda: store_file)
    app, _ = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_categories(client):
    resp = client.get("/api/lore/categories")
    assert resp.status_code == 200
    assert resp.get_json()["categories"] == lore_kb.LORE_CATEGORIES


def test_entries_empty(client):
    resp = client.get("/api/lore/entries")
    assert resp.status_code == 200
    assert resp.get_json()["entries"] == []


def test_crud_roundtrip(client):
    created = client.post(
        "/api/lore/entries",
        json={"title": "Capitale", "category": "places", "keys": ["capitale"]},
    )
    assert created.status_code == 201
    entry = created.get_json()
    assert entry["id"]
    assert entry["category"] == "places"
    eid = entry["id"]

    got = client.get(f"/api/lore/entries/{eid}")
    assert got.status_code == 200

    updated = client.put(f"/api/lore/entries/{eid}", json={"content": "x"})
    assert updated.status_code == 200
    assert updated.get_json()["content"] == "x"

    listed = client.get("/api/lore/entries?category=places")
    assert any(e["id"] == eid for e in listed.get_json()["entries"])

    deleted = client.delete(f"/api/lore/entries/{eid}")
    assert deleted.status_code == 200
    assert deleted.get_json()["deleted"] is True
    assert client.get(f"/api/lore/entries/{eid}").status_code == 404


def test_create_requires_title(client):
    assert client.post("/api/lore/entries", json={}).status_code == 400


def test_get_missing_404(client):
    assert client.get("/api/lore/entries/nope").status_code == 404
