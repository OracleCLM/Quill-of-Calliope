"""GAP-75: test per /api/chars e /api/char/<name>/facts routes in server.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from app.calliope_shell.server import create_app


@pytest.fixture
def client():
    app, _ = create_app()
    app.config["TESTING"] = True
    return app.test_client()


# ── GET /api/chars ────────────────────────────────────────────────────────────


def test_chars_list_returns_200(client):
    r = client.get("/api/chars")
    assert r.status_code == 200


def test_chars_list_returns_list(client):
    data = client.get("/api/chars").get_json()
    assert isinstance(data, list)


# ── POST /api/chars ───────────────────────────────────────────────────────────


def test_chars_upsert_returns_ok(client):
    r = client.post("/api/chars", json={"name": "TestChar"})
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_chars_upsert_missing_name_returns_400(client):
    r = client.post("/api/chars", json={})
    assert r.status_code == 400


def test_chars_upsert_empty_name_returns_400(client):
    r = client.post("/api/chars", json={"name": ""})
    assert r.status_code == 400


def test_chars_upsert_appears_in_list(client):
    client.post("/api/chars", json={"name": "Visibile"})
    chars = client.get("/api/chars").get_json()
    names = [c["name"] for c in chars]
    assert "Visibile" in names


# ── GET /api/chars/<name> ─────────────────────────────────────────────────────


def test_chars_get_existing_returns_200(client):
    client.post("/api/chars", json={"name": "Aurora"})
    r = client.get("/api/chars/Aurora")
    assert r.status_code == 200


def test_chars_get_missing_returns_404(client):
    r = client.get("/api/chars/PersonaggioInesistente9999")
    assert r.status_code == 404


# ── GET /api/char/<name>/facts ────────────────────────────────────────────────


def test_char_facts_list_returns_200(client):
    r = client.get("/api/char/AnyChar/facts")
    assert r.status_code == 200


def test_char_facts_list_returns_list(client):
    data = client.get("/api/char/AnyChar/facts").get_json()
    assert "facts" in data
