"""
Contract test (father-authored acceptance) — WI-23.

Il worker Efesto deve far passare questi test aggiungendo in
`app/calliope_shell/characters_db_routes.py`:

    PATCH /api/db/characters/<character_id>
    body JSON (tutti i campi opzionali): {"name"?: str, "kind"?: str, "image_path"?: str}
    -> 200 se aggiornato
    -> 400 se body JSON assente o vuoto ({})
    -> 404 se character_id non esiste

Usa SOLO: db_chars.update_character(conn, char_id, *, name=None, kind=None,
          image_path=None) -> bool
  app/db/characters.py:136 — keyword-only, ritorna False se char non esiste.

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


def _add(client, name="Luna", kind="npc"):
    return client.post("/api/db/characters", json={"name": name, "kind": kind}).get_json()["id"]


# --- WI-23: PATCH /api/db/characters/<id> ------------------------------------

def test_update_name_returns_200(client):
    cid = _add(client)
    r = client.patch(f"/api/db/characters/{cid}", json={"name": "Nuova Luna"})
    assert r.status_code == 200


def test_update_name_reflected_in_get(client):
    cid = _add(client, name="Vecchio")
    client.patch(f"/api/db/characters/{cid}", json={"name": "Nuovo"})
    data = client.get(f"/api/db/characters/{cid}").get_json()
    assert data["name"] == "Nuovo"


def test_update_kind_only(client):
    cid = _add(client, kind="npc")
    client.patch(f"/api/db/characters/{cid}", json={"kind": "player"})
    data = client.get(f"/api/db/characters/{cid}").get_json()
    assert data["kind"] == "player"


def test_update_not_found_404(client):
    r = client.patch("/api/db/characters/id-inesistente",
                     json={"name": "X"})
    assert r.status_code == 404


def test_update_empty_body_400(client):
    cid = _add(client)
    r = client.patch(f"/api/db/characters/{cid}", json={})
    assert r.status_code == 400
