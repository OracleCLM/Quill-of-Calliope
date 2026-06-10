"""
Contract test (father-authored acceptance) — WI-38.

Il worker Efesto deve far passare questi test creando:

1. In `app/db/scenes.py` la funzione:
       assign_scene_to_arc(conn: sqlite3.Connection, scene_id: str, arc_id: str | None) -> bool
       - aggiorna scenes.arc_id per scene_id
       - ritorna True se aggiornato, False se scene non esiste
       - arc_id puo' essere None (rimuove assegnazione)

2. Route in `app/calliope_shell/scenes_db_routes.py`:
       PATCH /api/db/scenes/<scene_id>/arc
       body JSON: {"arc_id": str | null}
       -> 200 se aggiornato (arc_id puo' essere null per disassociare)
       -> 400 se chiave "arc_id" assente dal body
       -> 404 se scene_id non esiste

3. Verificare che GET /api/db/scenes/<scene_id> restituisca arc_id aggiornato
   nel dizionario "scene".

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema, new_id
from app.calliope_shell.scenes_db_routes import register_scenes_db_routes


@pytest.fixture
def seeded(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    scene_id = new_id()
    arc_id = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "Scena Test"))
    conn.execute(
        "INSERT INTO arcs (id, title) VALUES (?, ?)", (arc_id, "Arco Test")
    )
    conn.commit()
    conn.close()
    return {"path": str(p), "scene_id": scene_id, "arc_id": arc_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# --- WI-38: PATCH /api/db/scenes/<id>/arc -----------------------------------

def test_assign_arc_returns_200(client):
    c, s = client
    r = c.patch(f"/api/db/scenes/{s['scene_id']}/arc", json={"arc_id": s["arc_id"]})
    assert r.status_code == 200


def test_assign_arc_reflected_in_detail(client):
    c, s = client
    c.patch(f"/api/db/scenes/{s['scene_id']}/arc", json={"arc_id": s["arc_id"]})
    detail = c.get(f"/api/db/scenes/{s['scene_id']}").get_json()
    assert detail["scene"]["arc_id"] == s["arc_id"]


def test_assign_arc_null_disassociates(client):
    c, s = client
    r1 = c.patch(f"/api/db/scenes/{s['scene_id']}/arc", json={"arc_id": s["arc_id"]})
    assert r1.status_code == 200  # se fallisce qui il test e' correttamente RED
    c.patch(f"/api/db/scenes/{s['scene_id']}/arc", json={"arc_id": None})
    detail = c.get(f"/api/db/scenes/{s['scene_id']}").get_json()
    assert detail["scene"]["arc_id"] is None


def test_assign_arc_missing_key_400(client):
    c, s = client
    r = c.patch(f"/api/db/scenes/{s['scene_id']}/arc", json={})
    assert r.status_code == 400


def test_assign_arc_scene_not_found_404(client):
    c, s = client
    r = c.patch("/api/db/scenes/scena-inesistente/arc", json={"arc_id": s["arc_id"]})
    assert r.status_code == 404
    # La route deve restituire JSON (non HTML di Flask per route inesistente)
    assert r.content_type == "application/json"
