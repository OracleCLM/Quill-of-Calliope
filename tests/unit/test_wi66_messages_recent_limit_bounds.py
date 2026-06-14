"""Contract test WI-66: bound del parametro `limit` su /api/db/messages/recent.

Gap robustezza (messages_db_routes.py): `limit = request.args.get("limit", type=int)` non
ha lower-bound. Con `?limit=-5` SQLite interpreta `LIMIT -5` come "nessun limite" e ritorna
TUTTE le righe (leak cross-scena non voluto); `?limit=0` ritorna comunque LIMIT 0 ambiguo.
Contratto: `limit <= 0` e' invalido -> 400 bad_request (stesso stile delle altre route del file).
Il limit valido resta invariato (regression guard).
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema, new_id
from app.calliope_shell.messages_db_routes import register_messages_db_routes


def _ins(conn, scene_id, author, content, ts, pos):
    conn.execute(
        "INSERT INTO messages (id, scene_id, author_name, content_original, ts, source, position_order) "
        "VALUES (?, ?, ?, ?, ?, 'manual', ?)",
        (new_id(), scene_id, author, content, ts, pos),
    )


@pytest.fixture
def client(tmp_path):
    p = tmp_path / "t.db"
    conn = get_db(p)
    init_schema(conn)
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", ("s1", "Scena 1"))
    _ins(conn, "s1", "Kikyo", "m1", "2021-01-01T01:00:00Z", 0)
    _ins(conn, "s1", "Quinn", "m2", "2021-01-01T02:00:00Z", 1)
    conn.commit()
    conn.close()
    app = Flask(__name__)
    register_messages_db_routes(app, db_path=str(p))
    return app.test_client()


def test_negative_limit_rejected(client):
    r = client.get("/api/db/messages/recent?limit=-5")
    assert r.status_code == 400
    assert "error" in (r.get_json() or {})


def test_zero_limit_rejected(client):
    r = client.get("/api/db/messages/recent?limit=0")
    assert r.status_code == 400
    assert "error" in (r.get_json() or {})


def test_valid_limit_still_ok(client):
    r = client.get("/api/db/messages/recent?limit=1")
    assert r.status_code == 200
    assert len(r.get_json()["messages"]) == 1
