"""GAP-4: importer Discord in-UI — scan / preview / to-scene."""

import json
import os
import tempfile

from flask import Flask

from app.calliope_shell.import_routes import register_import_routes
from app.db import get_db, init_schema
from app.db.messages import list_messages_for_scene


def _dce_export(d):
    dce = {
        "guild": {"id": "1"},
        "channel": {"id": "10", "name": "canale-test", "type": "GuildTextChat"},
        "messages": [
            {"id": "100", "timestamp": "2024-01-01T10:00:00",
             "author": {"id": "a1", "name": "Alice", "isBot": False},
             "type": "Default", "content": "UNO"},
            {"id": "101", "timestamp": "2024-01-01T10:01:00",
             "author": {"id": "a2", "name": "Bob", "isBot": False},
             "type": "Default", "content": "DUE"},
        ],
    }
    with open(os.path.join(d, "canale.json"), "w", encoding="utf-8") as f:
        json.dump(dce, f)


def _client(db):
    app = Flask(__name__)
    register_import_routes(app, db_path=db)
    return app.test_client()


def test_scan_preview_to_scene_flow():
    expdir = tempfile.mkdtemp(prefix="dce-")
    _dce_export(expdir)
    _fd, db = tempfile.mkstemp(suffix=".db")
    conn = get_db(db)
    init_schema(conn)
    conn.execute("INSERT INTO scenes(id,title,created_at,updated_at) "
                 "VALUES('s1','S',datetime('now'),datetime('now'))")
    conn.commit()
    conn.close()
    c = _client(db)

    scan = c.post("/api/import/discord/scan", json={"dir": expdir})
    assert scan.status_code == 200
    files = scan.get_json()["files"]
    assert files and files[0]["channel"] == "canale-test" and files[0]["count"] == 2

    prev = c.post("/api/import/discord/preview", json={"dir": expdir, "file": "canale.json"})
    assert prev.status_code == 200
    msgs = prev.get_json()["messages"]
    assert [m["author_name"] for m in msgs] == ["Alice", "Bob"]

    sel = [{"author_name": m["author_name"], "content": m["content"]} for m in msgs]
    imp = c.post("/api/import/discord/to-scene", json={"scene_id": "s1", "messages": sel})
    assert imp.status_code == 201
    assert imp.get_json()["imported"] == 2

    # stato-risultante: i messaggi sono nella scena, in coda e in ordine.
    conn = get_db(db)
    rows = list_messages_for_scene(conn, "s1")
    conn.close()
    assert [r["author_name"] for r in rows] == ["Alice", "Bob"]
    assert [r["content_original"] for r in rows] == ["UNO", "DUE"]


def test_scan_missing_dir_404():
    _fd, db = tempfile.mkstemp(suffix=".db")
    c = _client(db)
    assert c.post("/api/import/discord/scan", json={"dir": "/nope/zzz"}).status_code == 404
    assert c.post("/api/import/discord/scan", json={}).status_code == 400


def test_to_scene_unknown_scene_404():
    _fd, db = tempfile.mkstemp(suffix=".db")
    conn = get_db(db)
    init_schema(conn)
    conn.close()
    c = _client(db)
    r = c.post("/api/import/discord/to-scene",
               json={"scene_id": "nope", "messages": [{"author_name": "A", "content": "x"}]})
    assert r.status_code == 404
