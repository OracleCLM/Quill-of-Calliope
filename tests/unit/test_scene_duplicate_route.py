"""
Contract test (father-authored acceptance) — WI-16.

Il worker Efesto deve far passare questi test aggiungendo in
`app/calliope_shell/scenes_db_routes.py`:

    POST /api/db/scenes/<scene_id>/duplicate
         body JSON: {"new_name": str}
         -> 201 + {"new_scene_id": "<uuid>"}
         -> 400 se new_name assente o vuoto
         -> 404 se scene_id non esiste

Usa SOLO: db_messages.duplicate_scene(conn, scene_id, new_name)
  gia' in app/db/messages.py:531, importata come db_messages in scenes_db_routes.
  Firma esatta: duplicate_scene(conn, scene_id: str, new_name: str) -> str

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema, new_id
from app.db.messages import add_message
from app.calliope_shell.scenes_db_routes import register_scenes_db_routes


@pytest.fixture
def seeded(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    scene_id = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "Originale"))
    conn.commit()
    add_message(conn, scene_id=scene_id, author_name="Alice",
                content_original="primo", position_order=0)
    add_message(conn, scene_id=scene_id, author_name="Bob",
                content_original="secondo", position_order=1)
    conn.close()
    return {"path": str(p), "scene_id": scene_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# --- WI-16: duplicate scene --------------------------------------------------

def test_duplicate_returns_201_with_new_id(client):
    c, s = client
    r = c.post(f"/api/db/scenes/{s['scene_id']}/duplicate",
               json={"new_name": "Copia"})
    assert r.status_code == 201
    body = r.get_json()
    assert "new_scene_id" in body
    assert body["new_scene_id"] != s["scene_id"]


def test_duplicate_new_scene_has_same_messages(client):
    c, s = client
    new_id_val = c.post(
        f"/api/db/scenes/{s['scene_id']}/duplicate",
        json={"new_name": "Copia"},
    ).get_json()["new_scene_id"]
    detail = c.get(f"/api/db/scenes/{new_id_val}").get_json()
    assert len(detail["messages"]) == 2
    contents = {m["content_original"] for m in detail["messages"]}
    assert contents == {"primo", "secondo"}


def test_duplicate_original_scene_unchanged(client):
    c, s = client
    c.post(f"/api/db/scenes/{s['scene_id']}/duplicate", json={"new_name": "Copia"})
    original = c.get(f"/api/db/scenes/{s['scene_id']}").get_json()
    assert len(original["messages"]) == 2


def test_duplicate_missing_new_name_400(client):
    c, s = client
    r = c.post(f"/api/db/scenes/{s['scene_id']}/duplicate", json={})
    assert r.status_code == 400


def test_duplicate_unknown_scene_404(client):
    c, _ = client
    r = c.post("/api/db/scenes/scena-inesistente/duplicate",
               json={"new_name": "Copia"})
    assert r.status_code == 404
