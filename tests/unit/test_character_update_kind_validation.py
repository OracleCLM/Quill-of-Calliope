"""
Contract test (father-authored acceptance) — WI-63.

Il worker Efesto deve far passare questi test modificando
`app/calliope_shell/characters_db_routes.py`:

    PATCH /api/db/characters/<char_id> con kind non valido deve restituire 400
    (attuale: sqlite3.IntegrityError CHECK constraint -> 500 non gestito).

    La route DEVE validare kind PRIMA di chiamare db_chars.update_character()
    usando VALID_KINDS (gia' definito nel modulo a riga 5):
        if kind is not None and kind not in VALID_KINDS:
            return jsonify({"error": "invalid kind"}), 400

    Kind validi: 'operator', 'player', 'npc'
    Schema DB: CHECK (kind IN ('operator','player','npc'))
      app/db/migrations/001_scene_as_chat.sql

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema, new_id
from app.calliope_shell.characters_db_routes import register_characters_db_routes


@pytest.fixture
def seeded(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    char_id = new_id()
    conn.execute(
        "INSERT INTO characters (id, name, kind) VALUES (?, ?, ?)",
        (char_id, "Testchar", "npc"),
    )
    conn.commit()
    conn.close()
    return {"path": str(p), "char_id": char_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_characters_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# --- WI-63: PATCH kind validation --------------------------------------------

def test_patch_invalid_kind_returns_400(client):
    c, s = client
    r = c.patch(f"/api/db/characters/{s['char_id']}", json={"kind": "pirate"})
    assert r.status_code == 400


def test_patch_invalid_kind_does_not_modify_char(client):
    c, s = client
    c.patch(f"/api/db/characters/{s['char_id']}", json={"kind": "pirate"})
    char = c.get(f"/api/db/characters/{s['char_id']}").get_json()
    assert char["kind"] == "npc"


def test_patch_valid_kind_player_returns_200(client):
    c, s = client
    r = c.patch(f"/api/db/characters/{s['char_id']}", json={"kind": "player"})
    assert r.status_code == 200


def test_patch_valid_kind_operator_returns_200(client):
    c, s = client
    r = c.patch(f"/api/db/characters/{s['char_id']}", json={"kind": "operator"})
    assert r.status_code == 200


def test_patch_kind_update_persisted(client):
    c, s = client
    c.patch(f"/api/db/characters/{s['char_id']}", json={"kind": "player"})
    char = c.get(f"/api/db/characters/{s['char_id']}").get_json()
    assert char["kind"] == "player"
