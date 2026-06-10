"""
Contract test (father-authored acceptance) — WI-28.

Il worker Efesto deve far passare questi test modificando in
`app/calliope_shell/scenes_db_routes.py` la route POST /api/db/scenes/<id>/characters:

    POST /api/db/scenes/<id>/characters con stesso character_id gia' presente -> 409

La route DEVE gestire sqlite3.IntegrityError dal UNIQUE constraint
PRIMARY KEY (scene_id, character_id) in scene_characters.

Schema DB: PRIMARY KEY (scene_id, character_id)
  app/db/migrations/001_scene_as_chat.sql

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
    char_id = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "S"))
    conn.execute("INSERT INTO characters (id, name) VALUES (?, ?)", (char_id, "Luna"))
    conn.commit()
    conn.close()
    return {"path": str(p), "scene_id": scene_id, "char_id": char_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# --- WI-28: duplicate character in scene -> 409 ------------------------------

def test_first_add_returns_201(client):
    c, s = client
    r = c.post(f"/api/db/scenes/{s['scene_id']}/characters",
               json={"character_id": s["char_id"]})
    assert r.status_code == 201


def test_duplicate_add_returns_409(client):
    c, s = client
    c.post(f"/api/db/scenes/{s['scene_id']}/characters",
           json={"character_id": s["char_id"]})
    r = c.post(f"/api/db/scenes/{s['scene_id']}/characters",
               json={"character_id": s["char_id"]})
    assert r.status_code == 409


def test_duplicate_does_not_add_twice(client):
    c, s = client
    c.post(f"/api/db/scenes/{s['scene_id']}/characters",
           json={"character_id": s["char_id"]})
    c.post(f"/api/db/scenes/{s['scene_id']}/characters",
           json={"character_id": s["char_id"]})
    lst = c.get(f"/api/db/scenes/{s['scene_id']}/characters").get_json()["characters"]
    assert len(lst) == 1
