"""
Contract test (father-authored acceptance) — WI-42.

Il worker Efesto deve far passare questi test modificando:

1. `app/db/characters.py` — funzione list_characters_in_scene:
       SELECT c.*, sc.role
       FROM characters c
       JOIN scene_characters sc ON c.id = sc.character_id
       WHERE sc.scene_id = ?
   (attualmente: SELECT c.* — il campo role NON e' restituito)

2. La route GET /api/db/scenes/<scene_id>/characters (gia' in scenes_db_routes.py)
   usa list_characters_in_scene: il fix al punto 1 propaga automaticamente.

Risultato atteso: ogni dizionario personaggio nella risposta include il campo "role"
(es. "participant" di default, o il valore passato in POST /characters).

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
    conn.execute("INSERT INTO characters (id, name) VALUES (?, ?)", (char_id, "Ryo"))
    conn.commit()
    conn.close()
    return {"path": str(p), "scene_id": scene_id, "char_id": char_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# --- WI-42: role field nel roster personaggi di scena -----------------------

def test_character_in_scene_has_role_key(client):
    c, s = client
    c.post(
        f"/api/db/scenes/{s['scene_id']}/characters",
        json={"character_id": s["char_id"]},
    )
    chars = c.get(f"/api/db/scenes/{s['scene_id']}/characters").get_json()["characters"]
    assert len(chars) == 1
    assert "role" in chars[0]


def test_character_default_role_is_participant(client):
    c, s = client
    c.post(
        f"/api/db/scenes/{s['scene_id']}/characters",
        json={"character_id": s["char_id"]},
    )
    chars = c.get(f"/api/db/scenes/{s['scene_id']}/characters").get_json()["characters"]
    assert chars[0]["role"] == "participant"


def test_character_custom_role_preserved(client):
    c, s = client
    c.post(
        f"/api/db/scenes/{s['scene_id']}/characters",
        json={"character_id": s["char_id"], "role": "antagonist"},
    )
    chars = c.get(f"/api/db/scenes/{s['scene_id']}/characters").get_json()["characters"]
    assert chars[0]["role"] == "antagonist"
