"""Contract WI-PAGE-VALID: i parametri page/per_page non-numerici devono dare 400, non 500.

Gap (classe WI-66, validation): get_scene_messages_paginated (messages_db_routes.py:161-162) usa
`int(request.args.get("page",1))` / `int(request.args.get("per_page",50))` BARE -> su input
non-numerico (?page=abc) int() solleva ValueError -> 500 (errore server) invece di 400 bad_request.
Il check esistente copre solo <1, non il non-numerico. Fix: validare con type=int/try-except -> 400.
"""
import sys
import tempfile
from pathlib import Path

from flask import Flask

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db import get_db, init_schema  # noqa: E402
from app.calliope_shell.messages_db_routes import register_messages_db_routes  # noqa: E402


def _client():
    p = tempfile.mktemp(suffix=".db")
    conn = get_db(p)
    init_schema(conn)
    conn.execute(
        "INSERT INTO scenes(id, title, created_at, updated_at) "
        "VALUES ('s', 't', strftime('%Y-%m-%dT%H:%M:%SZ','now'), strftime('%Y-%m-%dT%H:%M:%SZ','now'))"
    )
    conn.commit()
    conn.close()
    app = Flask(__name__)
    register_messages_db_routes(app, db_path=p)
    return app.test_client()


def test_non_numeric_page_returns_400():
    r = _client().get("/api/db/scenes/s/messages?page=abc")
    assert r.status_code == 400


def test_non_numeric_per_page_returns_400():
    r = _client().get("/api/db/scenes/s/messages?per_page=xyz")
    assert r.status_code == 400


def test_valid_pagination_still_200():
    r = _client().get("/api/db/scenes/s/messages?page=1&per_page=10")
    assert r.status_code == 200
