"""
Contract test (father-authored acceptance) — WI-67.

Il worker Efesto deve aggiungere l'endpoint PATCH per aggiornare un arco
esistente, in `app/calliope_shell/arcs_db_routes.py`:

    PATCH /api/db/arcs/<arc_id>
      body JSON: {"title"?: str, "description"?: str}  (almeno uno)
      -> 200 + {"id": str, ...}   campi aggiornati persistiti
      -> 404 se l'arco non esiste
      -> 400 se il body non contiene alcun campo aggiornabile

Se serve, aggiungere in `app/db/arcs.py` una helper di update
(es. update_arc(conn, arc_id, **fields)) usando SOLO le API app.db esistenti.

Usa SOLO: from app.db import get_db, init_schema; from app.db.arcs (esistenti/nuove).
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


def _make_arc(client, title="The Iron Age", description="desc"):
    r = client.post("/api/db/arcs", json={"title": title, "description": description})
    assert r.status_code == 201
    return r.get_json()["id"]


# --- WI-67: PATCH /api/db/arcs/<arc_id> -------------------------------------

def test_patch_arc_updates_title(client):
    arc_id = _make_arc(client)
    r = client.patch(f"/api/db/arcs/{arc_id}", json={"title": "The Bronze Age"})
    assert r.status_code == 200
    # la modifica deve essere persistita
    g = client.get(f"/api/db/arcs/{arc_id}")
    assert g.status_code == 200
    assert g.get_json()["title"] == "The Bronze Age"


def test_patch_arc_updates_description_only(client):
    arc_id = _make_arc(client)
    r = client.patch(f"/api/db/arcs/{arc_id}", json={"description": "new desc"})
    assert r.status_code == 200
    g = client.get(f"/api/db/arcs/{arc_id}")
    assert g.get_json()["description"] == "new desc"


def test_patch_arc_missing_returns_404(client):
    r = client.patch("/api/db/arcs/does-not-exist", json={"title": "X"})
    assert r.status_code == 404


def test_patch_arc_no_fields_returns_400(client):
    arc_id = _make_arc(client)
    r = client.patch(f"/api/db/arcs/{arc_id}", json={})
    assert r.status_code == 400
