"""
Contract test (father-authored acceptance) — WI-59.

Il worker Efesto deve far passare questi test modificando in
`app/calliope_shell/scenes_db_routes.py` la route
POST /api/db/scenes/<scene_id>/characters (add_character_to_scene_route):

    BUG A: body senza "character_id" -> char_id = None ->
      SELECT id FROM characters WHERE id=None -> nessun risultato -> 404.
      Corretto HTTP: 400 bad_request (mancanza campo obbligatorio), non 404.

    BUG B: role = data.get("role", "") -> inserisce role="" nel DB.
      Lo schema definisce DEFAULT 'participant' per role, ma il DEFAULT
      non si applica se si passa un valore esplicito (anche "").
      Corretto: role = data.get("role") or "participant"

    FIX A: validare character_id prima del lookup DB:
        char_id = data.get("character_id")
        if not char_id:
            conn.close()
            return jsonify({"error": "character_id required"}), 400

    FIX B: usare "participant" come fallback per role vuoto/assente:
        role = data.get("role") or "participant"

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
    conn.execute("INSERT INTO characters (id, name) VALUES (?, ?)", (char_id, "Alice"))
    conn.commit()
    conn.close()
    return {"path": str(p), "scene_id": scene_id, "char_id": char_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# --- WI-59A: missing character_id -> 400 non 404 ----------------------------

def test_missing_character_id_returns_400(client):
    c, s = client
    r = c.post(f"/api/db/scenes/{s['scene_id']}/characters", json={})
    assert r.status_code == 400


def test_null_character_id_returns_400(client):
    c, s = client
    r = c.post(f"/api/db/scenes/{s['scene_id']}/characters",
               json={"character_id": None})
    assert r.status_code == 400


# --- WI-59B: role default -> "participant" non "" ---------------------------

def test_role_default_is_participant_not_empty(client):
    c, s = client
    c.post(f"/api/db/scenes/{s['scene_id']}/characters",
           json={"character_id": s["char_id"]})
    chars = c.get(f"/api/db/scenes/{s['scene_id']}/characters").get_json()["characters"]
    assert len(chars) == 1
    # Il ruolo non deve essere stringa vuota — test dipende da WI-42 (role nel roster)
    # Se WI-42 non e' ancora implementato, questo test fallisce per altra ragione
    # (role non presente nel dict) -> correttamente RED
    assert chars[0].get("role") == "participant"
