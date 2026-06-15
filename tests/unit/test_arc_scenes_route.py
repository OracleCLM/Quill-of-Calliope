"""
Contract test (father-authored acceptance) — WI-41.

Il worker Efesto deve far passare questi test aggiungendo:

1. In `app/db/arcs.py` (creato in WI-36) la funzione:
       list_scenes_for_arc(conn: sqlite3.Connection, arc_id: str) -> List[Mapping[str, object]]
       - ritorna lista di dizionari scene dove arc_id corrisponde
       - lista vuota se arc non ha scene assegnate
       - NON lancia eccezione se arc_id non esiste (ritorna lista vuota)

2. Route in `app/calliope_shell/arcs_db_routes.py` (creato in WI-36):
       GET /api/db/arcs/<arc_id>/scenes
       -> 200 + {"scenes": [...], "arc_id": arc_id}
       -> 404 se arc_id non esiste nel DB

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema, new_id
from app.calliope_shell.arcs_db_routes import register_arcs_db_routes


@pytest.fixture
def seeded(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    arc_id = new_id()
    conn.execute("INSERT INTO arcs (id, title) VALUES (?, ?)", (arc_id, "Arco Alpha"))
    scene_id_a = new_id()
    scene_id_b = new_id()
    conn.execute(
        "INSERT INTO scenes (id, title, arc_id) VALUES (?, ?, ?)",
        (scene_id_a, "Scena 1", arc_id),
    )
    conn.execute(
        "INSERT INTO scenes (id, title, arc_id) VALUES (?, ?, ?)",
        (scene_id_b, "Scena 2", arc_id),
    )
    unrelated = new_id()
    conn.execute(
        "INSERT INTO scenes (id, title) VALUES (?, ?)", (unrelated, "Scena Senza Arco")
    )
    conn.commit()
    conn.close()
    return {
        "path": str(p),
        "arc_id": arc_id,
        "scene_ids": {scene_id_a, scene_id_b},
        "unrelated_scene_id": unrelated,
    }


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_arcs_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# --- WI-41: GET /api/db/arcs/<arc_id>/scenes --------------------------------

def test_list_arc_scenes_returns_200(client):
    c, s = client
    r = c.get(f"/api/db/arcs/{s['arc_id']}/scenes")
    assert r.status_code == 200


def test_list_arc_scenes_response_shape(client):
    c, s = client
    data = c.get(f"/api/db/arcs/{s['arc_id']}/scenes").get_json()
    assert "scenes" in data
    assert data["arc_id"] == s["arc_id"]


def test_list_arc_scenes_returns_only_arc_scenes(client):
    c, s = client
    data = c.get(f"/api/db/arcs/{s['arc_id']}/scenes").get_json()
    returned_ids = {sc["id"] for sc in data["scenes"]}
    assert returned_ids == s["scene_ids"]
    assert s["unrelated_scene_id"] not in returned_ids


def test_list_arc_scenes_not_found_returns_404(client):
    c, _ = client
    r = c.get("/api/db/arcs/arco-inesistente/scenes")
    assert r.status_code == 404
