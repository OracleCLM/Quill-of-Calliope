"""Test della route POST /api/db/scenes/<sid>/messages/<mid>/refine (R1 wiring E3).

Il gateway-LLM e' mockato al confine HTTP (scene_refine.requests.post): nessuna
chiamata di rete. Verifica: 200 + content_enhanced ritornato e PERSISTITO, 404 su
scena/messaggio inesistenti.
"""

import tempfile

from flask import Flask

from app.calliope_shell import scene_refine
from app.calliope_shell.messages_db_routes import register_messages_db_routes
from app.db import get_db, init_schema, new_id
from app.db.characters import add_character_to_scene
from app.db.messages import add_message, get_message_by_id


class _FakeResp:
    ok = True

    def json(self):
        return {"content": "REFINED PROSE."}


def test_refine_route(monkeypatch):
    _fd, db_path = tempfile.mkstemp(suffix=".db")
    conn = get_db(db_path)
    init_schema(conn)
    sid = "s-refine"
    conn.execute(
        "INSERT INTO scenes(id,title,created_at,updated_at) "
        "VALUES(?,?,datetime('now'),datetime('now'))",
        (sid, "Refine Scene"),
    )
    cid = new_id()
    conn.execute(
        "INSERT INTO characters(id,name,created_at,updated_at) "
        "VALUES(?,?,datetime('now'),datetime('now'))",
        (cid, "Aria"),
    )
    conn.commit()
    add_character_to_scene(conn, sid, cid, role="protagonist")
    mid = add_message(
        conn,
        scene_id=sid,
        character_id=cid,
        author_name="Aria",
        content_original="The drago appears.",
    )
    conn.close()

    # Mock del gateway al confine HTTP (requests.post in scene_refine).
    monkeypatch.setattr(scene_refine.requests, "post", lambda *a, **k: _FakeResp())

    app = Flask(__name__)
    app.config["TESTING"] = True
    register_messages_db_routes(app, db_path=db_path)
    client = app.test_client()

    resp = client.post(f"/api/db/scenes/{sid}/messages/{mid}/refine")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["content_enhanced"] == "REFINED PROSE."
    assert data["content_original"] == "The drago appears."

    # Persistito nel DB.
    conn2 = get_db(db_path)
    assert get_message_by_id(conn2, mid)["content_enhanced"] == "REFINED PROSE."
    conn2.close()

    # 404 su scena/messaggio inesistenti.
    assert client.post(f"/api/db/scenes/nope/messages/{mid}/refine").status_code == 404
    assert client.post(f"/api/db/scenes/{sid}/messages/nope/refine").status_code == 404
