"""Contract test GAP-14: endpoint /api/db/arcs CRUD + arc→scenes."""
import pytest
from flask import Flask

from app.db import get_db, init_schema, new_id
from app.calliope_shell.arcs_db_routes import register_arcs_db_routes


@pytest.fixture
def client(tmp_path):
    p = tmp_path / "t.db"
    conn = get_db(p)
    init_schema(conn)
    conn.close()
    app = Flask(__name__)
    register_arcs_db_routes(app, db_path=str(p))
    return app.test_client(), str(p)


def test_create_arc(client):
    c, _ = client
    r = c.post("/api/db/arcs", json={"title": "L'Arco del Destino"})
    assert r.status_code == 201
    body = r.get_json()
    assert body["title"] == "L'Arco del Destino"
    assert "id" in body


def test_create_arc_missing_title(client):
    c, _ = client
    r = c.post("/api/db/arcs", json={})
    assert r.status_code == 400


def test_list_arcs_empty(client):
    c, _ = client
    r = c.get("/api/db/arcs")
    assert r.status_code == 200
    assert r.get_json()["arcs"] == []


def test_list_arcs_after_create(client):
    c, _ = client
    c.post("/api/db/arcs", json={"title": "Arc A"})
    c.post("/api/db/arcs", json={"title": "Arc B"})
    r = c.get("/api/db/arcs")
    arcs = r.get_json()["arcs"]
    assert len(arcs) == 2


def test_get_arc(client):
    c, _ = client
    arc_id = c.post("/api/db/arcs", json={"title": "Arc C"}).get_json()["id"]
    r = c.get(f"/api/db/arcs/{arc_id}")
    assert r.status_code == 200
    assert r.get_json()["title"] == "Arc C"


def test_get_arc_not_found(client):
    c, _ = client
    r = c.get("/api/db/arcs/nonexistent")
    assert r.status_code == 404


def test_delete_arc(client):
    c, _ = client
    arc_id = c.post("/api/db/arcs", json={"title": "Arc D"}).get_json()["id"]
    r = c.delete(f"/api/db/arcs/{arc_id}")
    assert r.status_code == 204
    assert c.get(f"/api/db/arcs/{arc_id}").status_code == 404


def test_delete_arc_not_found(client):
    c, _ = client
    r = c.delete("/api/db/arcs/nonexistent")
    assert r.status_code == 404


def test_arc_scenes_empty(client):
    c, _ = client
    arc_id = c.post("/api/db/arcs", json={"title": "Arc E"}).get_json()["id"]
    r = c.get(f"/api/db/arcs/{arc_id}/scenes")
    assert r.status_code == 200
    body = r.get_json()
    assert body["scenes"] == []
    assert body["arc_id"] == arc_id


def test_arc_scenes_not_found(client):
    c, _ = client
    r = c.get("/api/db/arcs/nonexistent/scenes")
    assert r.status_code == 404


def test_arc_scenes_with_assigned_scene(client, tmp_path):
    c, db_path = client
    arc_id = c.post("/api/db/arcs", json={"title": "Arc F"}).get_json()["id"]
    conn = get_db(db_path)
    scene_id = new_id()
    conn.execute(
        "INSERT INTO scenes (id, title, arc_id) VALUES (?, ?, ?)",
        (scene_id, "Scena 1", arc_id),
    )
    conn.commit()
    conn.close()
    r = c.get(f"/api/db/arcs/{arc_id}/scenes")
    assert r.status_code == 200
    scenes = r.get_json()["scenes"]
    assert len(scenes) == 1
