"""
Contract test (father-authored acceptance) — WI-43.

Il worker Efesto deve far passare questi test aggiungendo:

1. In `app/db/characters.py` la funzione:
       update_character_scene_role(
           conn: sqlite3.Connection,
           scene_id: str,
           character_id: str,
           role: str,
       ) -> bool
       - aggiorna scene_characters.role dove (scene_id, character_id) combacia
       - ritorna True se aggiornato, False se la coppia non esiste

2. Route in `app/calliope_shell/scenes_db_routes.py`:
       PATCH /api/db/scenes/<scene_id>/characters/<character_id>
       body JSON: {"role": str}
       -> 200 + {} se aggiornato
       -> 400 se "role" assente dal body
       -> 404 se il personaggio non e' nella scena

Usa SOLO: la nuova funzione update_character_scene_role.
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
    conn.execute("INSERT INTO characters (id, name) VALUES (?, ?)", (char_id, "Mira"))
    conn.execute(
        "INSERT INTO scene_characters (scene_id, character_id, role) VALUES (?, ?, ?)",
        (scene_id, char_id, "participant"),
    )
    conn.commit()
    conn.close()
    return {"path": str(p), "scene_id": scene_id, "char_id": char_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# --- WI-43: PATCH /api/db/scenes/<id>/characters/<char_id> -----------------

def test_update_role_returns_200(client):
    c, s = client
    r = c.patch(
        f"/api/db/scenes/{s['scene_id']}/characters/{s['char_id']}",
        json={"role": "protagonist"},
    )
    assert r.status_code == 200


def test_update_role_reflected_in_list(client):
    c, s = client
    c.patch(
        f"/api/db/scenes/{s['scene_id']}/characters/{s['char_id']}",
        json={"role": "protagonist"},
    )
    chars = c.get(
        f"/api/db/scenes/{s['scene_id']}/characters"
    ).get_json()["characters"]
    assert chars[0]["role"] == "protagonist"


def test_update_role_missing_field_400(client):
    c, s = client
    r = c.patch(
        f"/api/db/scenes/{s['scene_id']}/characters/{s['char_id']}",
        json={},
    )
    assert r.status_code == 400


def test_update_role_char_not_in_scene_404(client):
    c, s = client
    r = c.patch(
        f"/api/db/scenes/{s['scene_id']}/characters/char-inesistente",
        json={"role": "antagonist"},
    )
    assert r.status_code == 404
