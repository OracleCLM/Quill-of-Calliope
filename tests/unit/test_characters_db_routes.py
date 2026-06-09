"""
Contract test (father-authored acceptance) — WI-13.

Il worker Efesto deve far passare questi test creando
`app/calliope_shell/characters_db_routes.py` con:

    def register_characters_db_routes(app, *, db_path: str) -> None

che espone:

    GET  /api/db/characters          -> 200 + {"characters": [...]}
    POST /api/db/characters          -> 201 + {"id": "<uuid>"}
      body JSON: {"name": str, "kind"?: str}   (kind default "npc")
    GET  /api/db/characters/<id>     -> 200 + record | 404

Usa SOLO:
  app.db.characters.list_characters(conn) -> List[Mapping]
  app.db.characters.add_character(conn, *, name, kind) -> str (id)
  app.db.characters.get_character(conn, character_id) -> Mapping | None

NON modificare le assertion: sono il contratto di accettazione.
"""
import sys
from pathlib import Path

import pytest
from flask import Flask

from app.db import get_db, init_schema

sys.path.insert(0, str(Path(__file__).parents[2]))

try:
    from app.calliope_shell.characters_db_routes import register_characters_db_routes

    _MODULE_MISSING = False
except ImportError:
    _MODULE_MISSING = True


@pytest.fixture(autouse=True)
def require_module():
    if _MODULE_MISSING:
        pytest.fail(
            "app/calliope_shell/characters_db_routes.py mancante — "
            "implementare register_characters_db_routes con GET+POST /api/db/characters"
        )


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


# --- WI-13: characters DB CRUD ----------------------------------------------

def test_list_characters_empty(client):
    r = client.get("/api/db/characters")
    assert r.status_code == 200
    data = r.get_json()
    assert "characters" in data
    assert data["characters"] == []


def test_add_character_returns_201_with_id(client):
    r = client.post("/api/db/characters", json={"name": "Zara"})
    assert r.status_code == 201
    body = r.get_json()
    assert "id" in body
    assert isinstance(body["id"], str)
    assert len(body["id"]) > 0


def test_add_character_appears_in_list(client):
    char_id = client.post("/api/db/characters", json={"name": "Kira"}).get_json()["id"]
    lst = client.get("/api/db/characters").get_json()["characters"]
    ids = [ch["id"] for ch in lst]
    assert char_id in ids


def test_add_character_with_kind(client):
    r = client.post("/api/db/characters", json={"name": "Mira", "kind": "player"})
    assert r.status_code == 201
    char_id = r.get_json()["id"]
    detail = client.get(f"/api/db/characters/{char_id}").get_json()
    assert detail["kind"] == "player"


def test_get_character_detail(client):
    char_id = client.post("/api/db/characters", json={"name": "Reo"}).get_json()["id"]
    r = client.get(f"/api/db/characters/{char_id}")
    assert r.status_code == 200
    data = r.get_json()
    assert data["id"] == char_id
    assert data["name"] == "Reo"


def test_get_character_not_found_404(client):
    r = client.get("/api/db/characters/id-inesistente")
    assert r.status_code == 404


def test_add_character_missing_name_400(client):
    r = client.post("/api/db/characters", json={"kind": "npc"})
    assert r.status_code == 400
