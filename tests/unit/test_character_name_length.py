"""
Contract test (father-authored acceptance) — WI-55.

Il worker Efesto deve far passare questi test modificando in
`app/calliope_shell/characters_db_routes.py` la route
POST /api/db/characters (add_character_db):

    BUG: la route non cattura ValueError da db_chars.add_character() ->
    se name > 255 caratteri, add_character lancia ValueError("name non può
    superare 255 caratteri") -> 500.

    FIX: catturare ValueError prima o dopo la chiamata DB:
        # Opzione A: validazione nel route prima della chiamata DB
        if len(name) > 255:
            return jsonify({"error": "name too long"}), 400

        # Opzione B: try/except attorno alla chiamata
        try:
            char_id = db_chars.add_character(conn, name=name, kind=kind)
        except ValueError as exc:
            conn.close()
            return jsonify({"error": str(exc)}), 400

La funzione DB app/db/characters.py:add_character gia' valida
  (name non può superare 255 caratteri) ma la route non gestisce l'eccezione.

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema
from app.calliope_shell.characters_db_routes import register_characters_db_routes


@pytest.fixture
def client(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    conn.close()
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["PROPAGATE_EXCEPTIONS"] = False
    register_characters_db_routes(app, db_path=str(p))
    return app.test_client()


# --- WI-55: name > 255 caratteri -> 400 non 500 ----------------------------

def test_name_255_chars_accepted(client):
    r = client.post("/api/db/characters",
                    json={"name": "A" * 255, "kind": "npc"})
    assert r.status_code == 201


def test_name_256_chars_returns_400(client):
    r = client.post("/api/db/characters",
                    json={"name": "A" * 256, "kind": "npc"})
    assert r.status_code == 400


def test_name_300_chars_returns_400(client):
    r = client.post("/api/db/characters",
                    json={"name": "B" * 300, "kind": "npc"})
    assert r.status_code == 400


def test_normal_name_still_201(client):
    r = client.post("/api/db/characters",
                    json={"name": "Takeshi", "kind": "npc"})
    assert r.status_code == 201
