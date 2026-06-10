"""
Contract test (father-authored acceptance) — WI-56.

Il worker Efesto deve far passare questi test modificando in
`app/calliope_shell/scenes_db_routes.py` la route
PATCH /api/db/messages/<message_id>/position (db_update_message_position):

    BUG: la route valida che "position" sia un int ma NON che sia >= 0.
    position=-1 viene accettato (200) e passato a move_message() che
    muove il messaggio a una posizione negativa — comportamento indefinito.

    FIX: aggiungere controllo sul range:
        if position < 0:
            conn.close()
            return jsonify({"error": "bad_request"}), 400

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema, new_id
from app.db.messages import add_message
from app.calliope_shell.scenes_db_routes import register_scenes_db_routes


@pytest.fixture
def client(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    scene_id = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "S"))
    conn.commit()
    mid = add_message(conn, scene_id=scene_id, author_name="A",
                      content_original="x", position_order=0)
    conn.close()
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=str(p))
    return app.test_client(), mid


# --- WI-56: position negativa -> 400 non 200 --------------------------------

def test_negative_position_returns_400(client):
    c, mid = client
    r = c.patch(f"/api/db/messages/{mid}/position", json={"position": -1})
    assert r.status_code == 400


def test_negative_large_returns_400(client):
    c, mid = client
    r = c.patch(f"/api/db/messages/{mid}/position", json={"position": -100})
    assert r.status_code == 400


def test_zero_position_accepted(client):
    c, mid = client
    r = c.patch(f"/api/db/messages/{mid}/position", json={"position": 0})
    assert r.status_code == 200


def test_positive_position_accepted(client):
    c, mid = client
    r = c.patch(f"/api/db/messages/{mid}/position", json={"position": 5})
    assert r.status_code == 200
