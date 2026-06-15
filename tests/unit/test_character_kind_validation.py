"""
Contract test (father-authored acceptance) — WI-27.

Il worker Efesto deve far passare questi test modificando in
`app/calliope_shell/characters_db_routes.py` la route POST /api/db/characters:

    POST /api/db/characters con kind non valido -> 400
    kind validi: 'operator', 'player', 'npc'

La route DEVE validare kind PRIMA di chiamare db_chars.add_character()
(altrimenti sqlite3.IntegrityError CHECK constraint → 500 non gestito).

Schema DB: CHECK (kind IN ('operator','player','npc'))
  app/db/migrations/001_scene_as_chat.sql

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema
from app.calliope_shell.characters_db_routes import register_characters_db_routes

VALID_KINDS = ("operator", "player", "npc")


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


# --- WI-27: kind validation --------------------------------------------------

def test_invalid_kind_returns_400(client):
    r = client.post("/api/db/characters", json={"name": "X", "kind": "villain"})
    assert r.status_code == 400


def test_empty_kind_returns_400(client):
    r = client.post("/api/db/characters", json={"name": "X", "kind": ""})
    assert r.status_code == 400


@pytest.mark.parametrize("kind", VALID_KINDS)
def test_valid_kinds_return_201(client, kind):
    r = client.post("/api/db/characters", json={"name": f"Char_{kind}", "kind": kind})
    assert r.status_code == 201


def test_default_kind_is_npc(client):
    r = client.post("/api/db/characters", json={"name": "DefaultChar"})
    assert r.status_code == 201
    cid = r.get_json()["id"]
    data = client.get(f"/api/db/characters/{cid}").get_json()
    assert data["kind"] == "npc"
