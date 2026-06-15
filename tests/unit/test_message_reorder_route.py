"""
Contract test (father-authored acceptance) — WI-18.

Il worker Efesto deve far passare questi test aggiungendo in
`app/calliope_shell/scenes_db_routes.py`:

    PATCH /api/db/messages/<message_id>/position
    body JSON: {"position": int}
    -> 200 se spostato
    -> 400 se body mancante o position non intero
    -> 404 se message_id non esiste

Usa SOLO: db_messages.move_message(conn, message_id, new_position) -> bool
  app/db/messages.py:332 — ritorna False se msg non esiste.

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
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "S"))
    conn.commit()
    # 3 messaggi in ordine 0,1,2
    for i in range(3):
        add_message(conn, scene_id=scene_id, author_name=f"A{i}",
                    content_original=f"msg{i}", position_order=i)
    conn.close()
    return {"path": str(p), "scene_id": scene_id}


def _msg_ids_in_order(c, scene_id):
    msgs = c.get(f"/api/db/scenes/{scene_id}").get_json()["messages"]
    return [m["id"] for m in msgs]


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# --- WI-18: reorder message --------------------------------------------------

def test_move_message_returns_200(client):
    c, s = client
    mid = _msg_ids_in_order(c, s["scene_id"])[2]  # ultimo
    r = c.patch(f"/api/db/messages/{mid}/position", json={"position": 0})
    assert r.status_code == 200


def test_move_message_changes_order(client):
    c, s = client
    ids_before = _msg_ids_in_order(c, s["scene_id"])
    last_id = ids_before[2]
    c.patch(f"/api/db/messages/{last_id}/position", json={"position": 0})
    ids_after = _msg_ids_in_order(c, s["scene_id"])
    assert ids_after[0] == last_id


def test_move_message_not_found_404(client):
    c, _ = client
    r = c.patch("/api/db/messages/msg-inesistente/position", json={"position": 0})
    assert r.status_code == 404


def test_move_message_missing_body_400(client):
    c, s = client
    mid = _msg_ids_in_order(c, s["scene_id"])[0]
    r = c.patch(f"/api/db/messages/{mid}/position", json={})
    assert r.status_code == 400
