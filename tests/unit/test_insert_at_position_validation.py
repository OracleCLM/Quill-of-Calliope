"""
Contract test (father-authored acceptance) — WI-58.

Il worker Efesto deve far passare questi test modificando in
`app/calliope_shell/scenes_db_routes.py` la route
POST /api/db/scenes/<scene_id>/messages/insert (db_insert_message_at):

    BUG: la route controlla che "position_order" sia PRESENTE nel body
    ma NON valida che sia un intero non-negativo:
      - position_order="abc" -> 201 (stringa salvata come TEXT, comportamento indefinito)
      - position_order=-1   -> 201 (posizione negativa accettata)

    FIX: validare il tipo e il range:
        pos = body.get("position_order")
        if not isinstance(pos, int) or pos < 0:
            conn.close()
            return jsonify({"error": "bad_request"}), 400

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema, new_id
from app.calliope_shell.scenes_db_routes import register_scenes_db_routes


@pytest.fixture
def client(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    scene_id = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "S"))
    conn.commit()
    conn.close()
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=str(p))
    return app.test_client(), scene_id


def _insert(c, sid, **kw):
    payload = {"author_name": "A", "content_original": "x", **kw}
    return c.post(f"/api/db/scenes/{sid}/messages/insert", json=payload)


# --- WI-58: position_order validazione tipo e range -------------------------

def test_string_position_returns_400(client):
    c, sid = client
    r = _insert(c, sid, position_order="abc")
    assert r.status_code == 400


def test_negative_position_returns_400(client):
    c, sid = client
    r = _insert(c, sid, position_order=-1)
    assert r.status_code == 400


def test_float_position_returns_400(client):
    c, sid = client
    r = _insert(c, sid, position_order=1.5)
    assert r.status_code == 400


def test_zero_position_accepted(client):
    c, sid = client
    r = _insert(c, sid, position_order=0)
    assert r.status_code == 201


def test_positive_position_accepted(client):
    c, sid = client
    r = _insert(c, sid, position_order=3)
    assert r.status_code == 201
