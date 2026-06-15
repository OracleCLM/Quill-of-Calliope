"""
Contract test (father-authored acceptance) — WI-37.

Il worker Efesto deve far passare questi test aggiungendo in
`app/calliope_shell/arcs_db_routes.py` (creato in WI-36):

    Route:
      GET    /api/db/arcs/<arc_id>
             -> 200 + dizionario arco (id, title, description, ...)
             -> 404 se arc_id non esiste

      DELETE /api/db/arcs/<arc_id>
             -> 204 se eliminato
             -> 404 se arc_id non esiste

E aggiungere in `app/db/arcs.py`:
    get_arc(conn: sqlite3.Connection, arc_id: str) -> dict | None
    - ritorna dizionario se esiste, None se non esiste

    delete_arc(conn: sqlite3.Connection, arc_id: str) -> bool
    - ritorna True se eliminato, False se non esisteva

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema
from app.calliope_shell.arcs_db_routes import register_arcs_db_routes


@pytest.fixture
def seeded(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    conn.close()
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_arcs_db_routes(app, db_path=str(p))
    c = app.test_client()
    arc_id = c.post("/api/db/arcs", json={"title": "Era di Fuoco"}).get_json()["id"]
    return c, arc_id


# --- WI-37: GET /api/db/arcs/<arc_id> ---------------------------------------

def test_get_arc_returns_200(seeded):
    c, arc_id = seeded
    r = c.get(f"/api/db/arcs/{arc_id}")
    assert r.status_code == 200


def test_get_arc_response_shape(seeded):
    c, arc_id = seeded
    data = c.get(f"/api/db/arcs/{arc_id}").get_json()
    assert data["id"] == arc_id
    assert data["title"] == "Era di Fuoco"


def test_get_arc_not_found_returns_404(seeded):
    c, _ = seeded
    r = c.get("/api/db/arcs/arc-inesistente-xyz")
    assert r.status_code == 404


# --- WI-37: DELETE /api/db/arcs/<arc_id> ------------------------------------

def test_delete_arc_returns_204(seeded):
    c, arc_id = seeded
    r = c.delete(f"/api/db/arcs/{arc_id}")
    assert r.status_code == 204


def test_delete_arc_removes_from_list(seeded):
    c, arc_id = seeded
    c.delete(f"/api/db/arcs/{arc_id}")
    data = c.get("/api/db/arcs").get_json()
    ids = [a["id"] for a in data["arcs"]]
    assert arc_id not in ids


def test_delete_arc_not_found_returns_404(seeded):
    c, _ = seeded
    r = c.delete("/api/db/arcs/arc-inesistente-xyz")
    assert r.status_code == 404
