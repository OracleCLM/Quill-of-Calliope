"""
Contract test (father-authored acceptance) — WI-48.

Il worker Efesto deve far passare questi test modificando
`app/calliope_shell/scenes_db_routes.py` nella route
POST /api/db/scenes/<scene_id>/messages (db_append_message):

    Dopo la chiamata a db_messages.add_message(...), aggiornare
    scenes.last_activity_at per tenere traccia dell'ultima attivita':

        conn.execute(
            "UPDATE scenes SET last_activity_at = datetime('now') WHERE id = ?",
            (scene_id,)
        )
        conn.commit()

    Questo abilita il sorting per attivita' recente nel dashboard.

Comportamenti da verificare:
  - Prima di qualsiasi messaggio: last_activity_at e' NULL
  - Dopo append: last_activity_at e' NOT NULL
  - Scena con messaggio recente appare prima nell'elenco GET /api/db/scenes

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
    sid_a = new_id()
    sid_b = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (sid_a, "Scena A"))
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (sid_b, "Scena B"))
    conn.commit()
    conn.close()
    return {"path": str(p), "sid_a": sid_a, "sid_b": sid_b}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


def _append(c, scene_id):
    return c.post(
        f"/api/db/scenes/{scene_id}/messages",
        json={"author_name": "Alice", "content_original": "msg"},
    )


# --- WI-48: last_activity_at aggiornato dopo append -------------------------

def test_last_activity_null_before_any_message(client):
    c, s = client
    data = c.get(f"/api/db/scenes/{s['sid_a']}").get_json()
    assert data["scene"]["last_activity_at"] is None


def test_last_activity_set_after_append(client):
    c, s = client
    _append(c, s["sid_a"])
    data = c.get(f"/api/db/scenes/{s['sid_a']}").get_json()
    assert data["scene"]["last_activity_at"] is not None


def test_most_recently_active_scene_first_in_list(client):
    c, s = client
    _append(c, s["sid_a"])
    # Piccola pausa per garantire ts diverso in SQLite datetime
    _append(c, s["sid_b"])
    scenes = c.get("/api/db/scenes").get_json()["scenes"]
    ids = [sc["id"] for sc in scenes]
    # sid_b aggiornato per ultimo -> deve essere prima
    assert ids.index(s["sid_b"]) < ids.index(s["sid_a"])
