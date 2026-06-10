"""
Contract test (father-authored acceptance) — WI-44.

Il worker Efesto deve far passare questi test modificando in
`app/calliope_shell/scenes_db_routes.py` la route GET /api/db/scenes:

    GET /api/db/scenes?arc_id=<arc_id>
    -> 200 + {"scenes": [...]}  (solo scene con arc_id corrispondente)

    GET /api/db/scenes          (senza parametro)
    -> 200 + {"scenes": [...]}  (tutte le scene — comportamento invariato)

Modifica: leggere request.args.get("arc_id") e aggiungere WHERE arc_id = ?
se presente nella query.

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
    arc_id = new_id()
    conn.execute("INSERT INTO arcs (id, title) VALUES (?, ?)", (arc_id, "Arco Alpha"))
    sid_a = new_id()
    sid_b = new_id()
    sid_no_arc = new_id()
    conn.execute(
        "INSERT INTO scenes (id, title, arc_id) VALUES (?, ?, ?)", (sid_a, "Scena A", arc_id)
    )
    conn.execute(
        "INSERT INTO scenes (id, title, arc_id) VALUES (?, ?, ?)", (sid_b, "Scena B", arc_id)
    )
    conn.execute(
        "INSERT INTO scenes (id, title) VALUES (?, ?)", (sid_no_arc, "Scena Senza Arco")
    )
    conn.commit()
    conn.close()
    return {
        "path": str(p),
        "arc_id": arc_id,
        "arc_scene_ids": {sid_a, sid_b},
        "no_arc_scene_id": sid_no_arc,
    }


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# --- WI-44: GET /api/db/scenes?arc_id= --------------------------------------

def test_filter_by_arc_returns_200(client):
    c, s = client
    r = c.get(f"/api/db/scenes?arc_id={s['arc_id']}")
    assert r.status_code == 200


def test_filter_by_arc_returns_only_arc_scenes(client):
    c, s = client
    data = c.get(f"/api/db/scenes?arc_id={s['arc_id']}").get_json()
    returned_ids = {sc["id"] for sc in data["scenes"]}
    assert returned_ids == s["arc_scene_ids"]


def test_filter_by_arc_excludes_unrelated_scenes(client):
    c, s = client
    data = c.get(f"/api/db/scenes?arc_id={s['arc_id']}").get_json()
    ids = {sc["id"] for sc in data["scenes"]}
    assert s["no_arc_scene_id"] not in ids


def test_no_arc_filter_returns_all_scenes(client):
    c, s = client
    data = c.get("/api/db/scenes").get_json()
    ids = {sc["id"] for sc in data["scenes"]}
    assert s["no_arc_scene_id"] in ids
    assert s["arc_scene_ids"].issubset(ids)


def test_filter_by_nonexistent_arc_returns_empty(client):
    c, _ = client
    data = c.get("/api/db/scenes?arc_id=arco-inesistente").get_json()
    assert data["scenes"] == []
