"""Regression del bug message-render: append in scene con position_order non-contigui.

Le scene importate da Discord hanno position_order grandi/non-contigui (es. 66..16541).
Il nuovo turno DEVE finire in CODA (position > max esistente), non a metà/in cima.
"""

import tempfile

from flask import Flask

from app.calliope_shell.messages_db_routes import register_messages_db_routes
from app.db import get_db, init_schema, new_id
from app.db.messages import add_message, list_messages_for_scene


def _seed_scene_with_sparse_positions(db_path):
    conn = get_db(db_path)
    init_schema(conn)
    sid = "s-import"
    conn.execute(
        "INSERT INTO scenes(id,title,created_at,updated_at) "
        "VALUES(?,?,datetime('now'),datetime('now'))",
        (sid, "Imported"),
    )
    conn.commit()
    # Posizioni non-contigue come nei dati Discord importati.
    for pos, txt in [(66, "primo"), (67, "secondo"), (16541, "ultimo-importato")]:
        add_message(
            conn,
            scene_id=sid,
            author_name="Aria",
            content_original=txt,
            position_order=pos,
        )
    conn.close()
    return sid


def test_append_goes_to_tail_with_sparse_positions():
    _fd, db_path = tempfile.mkstemp(suffix=".db")
    sid = _seed_scene_with_sparse_positions(db_path)

    app = Flask(__name__)
    app.config["TESTING"] = True
    register_messages_db_routes(app, db_path=db_path)
    client = app.test_client()

    resp = client.post(
        f"/api/db/scenes/{sid}/messages",
        json={"author_name": "Narratore", "content_original": "NUOVO TURNO"},
    )
    assert resp.status_code == 201
    new_id_ = resp.get_json()["id"]

    conn = get_db(db_path)
    msgs = list_messages_for_scene(conn, sid)
    conn.close()

    # Il nuovo turno DEVE essere l'ULTIMO nell'ordine renderizzato (position_order).
    assert msgs[-1]["id"] == new_id_, "il nuovo messaggio non è in coda"
    assert msgs[-1]["content_original"] == "NUOVO TURNO"
    # E la sua position deve superare il max preesistente (16541), non valere len()=3.
    assert msgs[-1]["position_order"] > 16541


def test_append_empty_scene_starts_at_zero():
    _fd, db_path = tempfile.mkstemp(suffix=".db")
    conn = get_db(db_path)
    init_schema(conn)
    sid = new_id()
    conn.execute(
        "INSERT INTO scenes(id,title,created_at,updated_at) "
        "VALUES(?,?,datetime('now'),datetime('now'))",
        (sid, "Vuota"),
    )
    conn.commit()
    conn.close()

    app = Flask(__name__)
    register_messages_db_routes(app, db_path=db_path)
    client = app.test_client()
    resp = client.post(
        f"/api/db/scenes/{sid}/messages",
        json={"author_name": "Narratore", "content_original": "Primo"},
    )
    assert resp.status_code == 201
    conn = get_db(db_path)
    msgs = list_messages_for_scene(conn, sid)
    conn.close()
    assert len(msgs) == 1
    assert msgs[0]["position_order"] == 0
