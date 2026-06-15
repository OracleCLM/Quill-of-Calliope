"""
Contract test (father-authored acceptance) — WI-39.

Il worker Efesto deve far passare questi test aggiungendo:

1. In `app/db/reactions.py` la funzione:
       delete_reaction(conn: sqlite3.Connection, reaction_id: str) -> bool
       - elimina la riga in scene_reactions con id = reaction_id
       - ritorna True se eliminata, False se non esisteva

2. Route in `app/calliope_shell/scenes_db_routes.py`:
       DELETE /api/db/messages/<message_id>/reactions/<reaction_id>
       -> 204 se eliminata
       -> 404 se reaction_id non esiste

   Note: message_id nel path e' per consistenza REST; la validazione
   puo' usare solo reaction_id per semplicita'.

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
    char_id = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "S"))
    conn.execute(
        "INSERT INTO characters (id, name) VALUES (?, ?)", (char_id, "Alice")
    )
    conn.commit()
    msg_id = add_message(
        conn, scene_id=scene_id, author_name="Alice", content_original="ciao", position_order=0
    )
    conn.close()
    return {"path": str(p), "scene_id": scene_id, "msg_id": msg_id, "char_id": char_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


def _add_reaction(c, msg_id, char_id):
    """Helper: aggiunge reazione e ritorna reaction_id."""
    r = c.post(
        f"/api/db/messages/{msg_id}/reactions",
        json={"character_id": char_id, "emoji": "👍"},
    )
    return r.get_json()["id"]


# --- WI-39: DELETE /api/db/messages/<msg_id>/reactions/<reaction_id> --------

def test_delete_reaction_returns_204(client):
    c, s = client
    rid = _add_reaction(c, s["msg_id"], s["char_id"])
    r = c.delete(f"/api/db/messages/{s['msg_id']}/reactions/{rid}")
    assert r.status_code == 204


def test_delete_reaction_removes_from_list(client):
    c, s = client
    rid = _add_reaction(c, s["msg_id"], s["char_id"])
    c.delete(f"/api/db/messages/{s['msg_id']}/reactions/{rid}")
    data = c.get(f"/api/db/messages/{s['msg_id']}/reactions").get_json()
    ids = [rx["id"] for rx in data["reactions"]]
    assert rid not in ids


def test_delete_reaction_not_found_returns_404(client):
    c, s = client
    # Prima verifica che la route DELETE esista (non 405)
    rid = _add_reaction(c, s["msg_id"], s["char_id"])
    assert c.delete(f"/api/db/messages/{s['msg_id']}/reactions/{rid}").status_code == 204
    r = c.delete(f"/api/db/messages/{s['msg_id']}/reactions/reaction-inesistente")
    assert r.status_code == 404
