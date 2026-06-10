"""
Contract test (father-authored acceptance) — WI-24.

Il worker Efesto deve far passare questi test aggiungendo in
`app/calliope_shell/characters_db_routes.py`:

    DELETE /api/db/characters/<character_id>
    -> 204 se eliminato
    -> 404 se character_id non esiste

Usa SOLO: db_chars.delete_character(conn, character_id) -> bool
  app/db/characters.py:204 — ritorna True se eliminato, False se non esisteva.

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema
from app.calliope_shell.characters_db_routes import register_characters_db_routes


@pytest.fixture
def client(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    conn.close()
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_characters_db_routes(app, db_path=str(p))
    return app.test_client()


def _add(client, name="Luna"):
    return client.post("/api/db/characters", json={"name": name}).get_json()["id"]


# --- WI-24: DELETE /api/db/characters/<id> -----------------------------------

def test_delete_returns_204(client):
    cid = _add(client)
    r = client.delete(f"/api/db/characters/{cid}")
    assert r.status_code == 204


def test_delete_removes_from_list(client):
    cid = _add(client)
    client.delete(f"/api/db/characters/{cid}")
    lst = client.get("/api/db/characters").get_json()["characters"]
    ids = [ch["id"] for ch in lst]
    assert cid not in ids


def test_delete_get_returns_404_after(client):
    cid = _add(client)
    client.delete(f"/api/db/characters/{cid}")
    r = client.get(f"/api/db/characters/{cid}")
    assert r.status_code == 404


def test_delete_not_found_404(client):
    r = client.delete("/api/db/characters/id-inesistente")
    assert r.status_code == 404


def test_delete_idempotent_second_call_404(client):
    cid = _add(client)
    client.delete(f"/api/db/characters/{cid}")
    r = client.delete(f"/api/db/characters/{cid}")
    assert r.status_code == 404
