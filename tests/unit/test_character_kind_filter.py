"""
Contract test (father-authored acceptance) — WI-26.

Il worker Efesto deve far passare questi test modificando in
`app/calliope_shell/characters_db_routes.py` la route GET /api/db/characters:

    GET /api/db/characters?kind=<kind>
    -> 200 + {"characters": [...]}  (filtrati per kind se ?kind= presente)
    -> senza ?kind= ritorna tutti (comportamento attuale invariato)

Usa SOLO: db_chars.list_characters(conn, kind=kind)
  app/db/characters.py:105 — kind=None ritorna tutti, kind="npc" ritorna solo npc.

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
    c = app.test_client()
    # seed: 2 npc, 1 player, 1 operator
    c.post("/api/db/characters", json={"name": "NPC_1", "kind": "npc"})
    c.post("/api/db/characters", json={"name": "NPC_2", "kind": "npc"})
    c.post("/api/db/characters", json={"name": "Player_1", "kind": "player"})
    c.post("/api/db/characters", json={"name": "Op_1", "kind": "operator"})
    return c


# --- WI-26: kind filter -------------------------------------------------------

def test_filter_npc_returns_only_npc(client):
    data = client.get("/api/db/characters?kind=npc").get_json()
    names = [c["name"] for c in data["characters"]]
    assert all("NPC" in n for n in names)
    assert len(names) == 2


def test_filter_player_returns_only_player(client):
    data = client.get("/api/db/characters?kind=player").get_json()
    assert len(data["characters"]) == 1
    assert data["characters"][0]["name"] == "Player_1"


def test_no_filter_returns_all(client):
    data = client.get("/api/db/characters").get_json()
    assert len(data["characters"]) == 4


def test_filter_unknown_kind_returns_empty(client):
    data = client.get("/api/db/characters?kind=villain").get_json()
    assert data["characters"] == []
