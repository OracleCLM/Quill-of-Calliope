"""Contract test WI-NAVMSG-1 (post-import sbloccato): endpoint recent-messages dal DB.

Il pannello 'Messaggi recenti' (nav-messages, orfano dopo FE-4) ora che il DB ha 12151 msg
puo' mostrare i messaggi recenti. Serve un endpoint GET /api/db/messages/recent che li
ritorni cross-scena (ORDER BY ts DESC), con limit e filtro opzionale per personaggio.
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
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", ("s2", "Scena 2"))
    _ins(conn, "s1", "Kikyo", "m1", "2021-01-01T01:00:00Z", 0)
    _ins(conn, "s1", "Quinn", "m2", "2021-01-01T02:00:00Z", 1)
    _ins(conn, "s2", "Kikyo", "m3", "2021-01-01T03:00:00Z", 0)
    conn.commit()
    conn.close()
    app = Flask(__name__)
    register_messages_db_routes(app, db_path=str(p))
    return app.test_client()


def test_recent_returns_messages(client):
    r = client.get("/api/db/messages/recent")
    assert r.status_code == 200
    msgs = (r.get_json() or {}).get("messages")
    assert isinstance(msgs, list) and len(msgs) == 3


def test_recent_respects_limit(client):
    r = client.get("/api/db/messages/recent?limit=2")
    assert r.status_code == 200
    assert len(r.get_json()["messages"]) == 2


def test_recent_filters_by_char(client):
    r = client.get("/api/db/messages/recent?char=Kikyo")
    assert r.status_code == 200
    msgs = r.get_json()["messages"]
    assert len(msgs) == 2
    assert all(m["author_name"] == "Kikyo" for m in msgs)


def test_recent_filters_by_char_partial(client):
    """GAP-9: filtro per stringa parziale (LIKE, non exact-match)."""
    r = client.get("/api/db/messages/recent?char=kiky")
    assert r.status_code == 200
    msgs = r.get_json()["messages"]
    assert len(msgs) == 2
    assert all("Kikyo" in m["author_name"] for m in msgs)


def test_recent_filters_by_char_case_insensitive(client):
    r = client.get("/api/db/messages/recent?char=KIKYO")
    assert r.status_code == 200
    assert len(r.get_json()["messages"]) == 2


def test_recent_message_shape(client):
    r = client.get("/api/db/messages/recent?limit=1")
    m = r.get_json()["messages"][0]
    for k in ("id", "scene_id", "author_name", "content_original", "ts"):
        assert k in m
