"""
Contract test (father-authored acceptance) — WI-36.

Il worker Efesto deve far passare questi test creando:

1. `app/db/arcs.py` con le funzioni:
       create_arc(conn: sqlite3.Connection, title: str, description: str = "") -> str
       - raise ValueError se title e' vuoto
       - inserisce riga in arcs(id, title, description) e ritorna id UUID

       list_arcs(conn: sqlite3.Connection) -> List[Mapping[str, object]]
       - ritorna lista di dizionari (tutti i campi di arcs)
       - ordinati per created_at DESC

2. `app/calliope_shell/arcs_db_routes.py` con:
       register_arcs_db_routes(app, *, db_path: str = None) -> None
       Route:
         POST /api/db/arcs
           body JSON: {"title": str, "description"?: str}
           -> 201 + {"id": str, "title": str}
           -> 400 se title assente o stringa vuota
         GET  /api/db/arcs
           -> 200 + {"arcs": [{id, title, description, created_at, ...}, ...]}

3. Registrare register_arcs_db_routes in `app/calliope_shell/server.py:create_app()`.

Usa SOLO: le funzioni di app.db.arcs (nuove).
NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema
from app.calliope_shell.arcs_db_routes import register_arcs_db_routes


@pytest.fixture
def client(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    conn.close()
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_arcs_db_routes(app, db_path=str(p))
    return app.test_client()


# --- WI-36: POST /api/db/arcs -----------------------------------------------

def test_create_arc_returns_201(client):
    r = client.post("/api/db/arcs", json={"title": "The Iron Age"})
    assert r.status_code == 201


def test_create_arc_response_shape(client):
    r = client.post("/api/db/arcs", json={"title": "The Iron Age"})
    body = r.get_json()
    assert "id" in body and body["id"]
    assert body["title"] == "The Iron Age"


def test_create_arc_missing_title_returns_400(client):
    r = client.post("/api/db/arcs", json={"description": "nessun titolo"})
    assert r.status_code == 400


def test_create_arc_empty_title_returns_400(client):
    r = client.post("/api/db/arcs", json={"title": ""})
    assert r.status_code == 400


# --- WI-36: GET /api/db/arcs ------------------------------------------------

def test_list_arcs_returns_200(client):
    r = client.get("/api/db/arcs")
    assert r.status_code == 200


def test_list_arcs_empty_on_fresh_db(client):
    data = client.get("/api/db/arcs").get_json()
    assert data["arcs"] == []


def test_list_arcs_includes_created(client):
    client.post("/api/db/arcs", json={"title": "Era dei Draghi"})
    data = client.get("/api/db/arcs").get_json()
    titles = [a["title"] for a in data["arcs"]]
    assert "Era dei Draghi" in titles
