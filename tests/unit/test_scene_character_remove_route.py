"""
Contract test (father-authored acceptance) — WI-19.

Il worker Efesto deve far passare questi test aggiungendo in
`app/calliope_shell/scenes_db_routes.py`:

    DELETE /api/db/scenes/<scene_id>/characters/<character_id>
    -> 204 se rimosso
    -> 404 se l'associazione non esiste (char non in scena, o scene/char inesistenti)

Usa SOLO: db_characters.remove_character_from_scene(conn, scene_id, char_id) -> bool
  app/db/characters.py:294 — ritorna True se rimosso, False se non era presente.
  Richiede: from app.db import characters as db_characters (gia' aggiunto in WI-15).

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema, new_id
from app.db.characters import add_character_to_scene
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
    add_character_to_scene(conn, scene_id, char_id)
    conn.close()
    return {"path": str(p), "scene_id": scene_id, "char_id": char_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# --- WI-19: remove character from scene -------------------------------------

def test_remove_character_returns_204(client):
    c, s = client
    r = c.delete(f"/api/db/scenes/{s['scene_id']}/characters/{s['char_id']}")
    assert r.status_code == 204


def test_remove_character_disappears_from_list(client):
    c, s = client
    c.delete(f"/api/db/scenes/{s['scene_id']}/characters/{s['char_id']}")
    lst = c.get(f"/api/db/scenes/{s['scene_id']}/characters").get_json()["characters"]
    ids = [ch["id"] for ch in lst]
    assert s["char_id"] not in ids


def test_remove_character_not_in_scene_404(client):
    c, s = client
    other_char = new_id()  # char non associato a nessuna scena
    r = c.delete(f"/api/db/scenes/{s['scene_id']}/characters/{other_char}")
    assert r.status_code == 404


def test_remove_character_idempotent_second_call_404(client):
    c, s = client
    c.delete(f"/api/db/scenes/{s['scene_id']}/characters/{s['char_id']}")
    r = c.delete(f"/api/db/scenes/{s['scene_id']}/characters/{s['char_id']}")
    assert r.status_code == 404
