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


# ── R-CALLIOPE-ME-DISCORD-LIVE: span + multi-canale + live ──────────────────────

def _dce_export_named(d, fname, channel_name, channel_id, msgs):
    dce = {
        "guild": {"id": "1"},
        "channel": {"id": channel_id, "name": channel_name, "type": "GuildTextChat",
                    "category": "RP"},
        "messages": [
            {"id": m[0], "timestamp": m[1],
             "author": {"id": "a", "name": m[2], "isBot": False},
             "type": "Default", "content": m[3]}
            for m in msgs
        ],
    }
    with open(os.path.join(d, fname), "w", encoding="utf-8") as f:
        json.dump(dce, f)


def _new_db_with_scene():
    _fd, db = tempfile.mkstemp(suffix=".db")
    conn = get_db(db)
    init_schema(conn)
    conn.execute("INSERT INTO scenes(id,title,created_at,updated_at) "
                 "VALUES('s1','S',datetime('now'),datetime('now'))")
    conn.commit()
    conn.close()
    return db


def test_scan_returns_channel_metadata():
    expdir = tempfile.mkdtemp(prefix="dce-")
    _dce_export_named(expdir, "ch.json", "alpha", "10", [
        ("1", "2024-01-01T10:00:00", "Alice", "UNO"),
        ("2", "2024-01-03T10:00:00", "Bob", "DUE"),
    ])
    c = _client(tempfile.mkstemp(suffix=".db")[1])
    scan = c.post("/api/import/discord/scan", json={"dir": expdir})
    assert scan.status_code == 200
    f = scan.get_json()["files"][0]
    assert f["channel"] == "alpha" and f["count"] == 2
    assert f["channel_id"] == "10" and f["parent_category"] == "RP"
    assert f["date_from"] == "2024-01-01T10:00:00"
    assert f["date_to"] == "2024-01-03T10:00:00"


def test_preview_span_filter():
    expdir = tempfile.mkdtemp(prefix="dce-")
    _dce_export_named(expdir, "ch.json", "alpha", "10", [
        ("1", "2024-01-01T10:00:00", "Early", "OUT_BEFORE"),
        ("2", "2024-01-05T10:00:00", "Mid", "IN_RANGE"),
        ("3", "2024-01-10T10:00:00", "Late", "OUT_AFTER"),
    ])
    c = _client(tempfile.mkstemp(suffix=".db")[1])
    prev = c.post("/api/import/discord/preview", json={
        "dir": expdir, "file": "ch.json",
        "since": "2024-01-03T00:00:00", "until": "2024-01-07T00:00:00",
    })
    assert prev.status_code == 200
    authors = [m["author_name"] for m in prev.get_json()["messages"]]
    assert authors == ["Mid"]


def test_preview_no_span_unchanged():
    expdir = tempfile.mkdtemp(prefix="dce-")
    _dce_export_named(expdir, "ch.json", "alpha", "10", [
        ("1", "2024-01-01T10:00:00", "A", "x"),
        ("2", "2024-01-05T10:00:00", "B", "y"),
    ])
    c = _client(tempfile.mkstemp(suffix=".db")[1])
    prev = c.post("/api/import/discord/preview", json={"dir": expdir, "file": "ch.json"})
    assert prev.get_json()["count"] == 2


def test_preview_multi_channel():
    expdir = tempfile.mkdtemp(prefix="dce-")
    _dce_export_named(expdir, "a.json", "alpha", "10",
                      [("1", "2024-01-01T10:00:00", "Alice", "A1")])
    _dce_export_named(expdir, "b.json", "beta", "20",
                      [("2", "2024-01-02T10:00:00", "Bob", "B1")])
    c = _client(tempfile.mkstemp(suffix=".db")[1])
    prev = c.post("/api/import/discord/preview", json={
        "dir": expdir, "files": ["a.json", "b.json"],
    })
    assert prev.status_code == 200
    body = prev.get_json()
    assert body["count"] == 2
    assert set(body["channels"]) == {"alpha", "beta"}


def test_to_scene_server_side_span():
    expdir = tempfile.mkdtemp(prefix="dce-")
    _dce_export_named(expdir, "ch.json", "alpha", "10", [
        ("1", "2024-01-01T10:00:00", "Early", "OUT"),
        ("2", "2024-01-05T10:00:00", "Mid", "IN"),
        ("3", "2024-01-10T10:00:00", "Late", "OUT2"),
    ])
    db = _new_db_with_scene()
    c = _client(db)
    imp = c.post("/api/import/discord/to-scene", json={
        "scene_id": "s1", "dir": expdir, "files": ["ch.json"],
        "since": "2024-01-03", "until": "2024-01-07",
    })
    assert imp.status_code == 201
    assert imp.get_json()["imported"] == 1
    conn = get_db(db)
    rows = list_messages_for_scene(conn, "s1")
    conn.close()
    assert [r["author_name"] for r in rows] == ["Mid"]


def test_live_invokes_dce_with_correct_flags():
    from app.calliope_shell import discord_live

    captured = {}
    expdir = tempfile.mkdtemp(prefix="dce-live-")

    def fake_runner(cmd, **kwargs):
        captured["cmd"] = cmd
        # Simula DCE che scrive un export.
        _dce_export_named(expdir, "out.json", "alpha", "10",
                          [("1", "2024-01-05T10:00:00", "Mid", "HELLO")])

        class _P:
            returncode = 0
            stdout = ""
            stderr = ""
        return _P()

    c = _client(tempfile.mkstemp(suffix=".db")[1])
    import unittest.mock as mock
    with mock.patch.object(discord_live, "dce_available", return_value=True), \
         mock.patch.object(discord_live, "_get_secret", return_value="FAKE_TOKEN"), \
         mock.patch("subprocess.run", side_effect=fake_runner):
        r = c.post("/api/import/discord/live", json={
            "channel_ids": ["111", "222"],
            "since": "2024-01-01", "until": "2024-01-10",
            "out_dir": expdir,
        })
    assert r.status_code == 200, r.get_json()
    cmd = captured["cmd"]
    assert "exportchannel" in cmd
    assert "-c" in cmd and "111" in cmd and "222" in cmd
    assert "--after" in cmd and "2024-01-01" in cmd
    assert "--before" in cmd and "2024-01-10" in cmd
    assert "FAKE_TOKEN" in cmd
    files = r.get_json()["files"]
    assert files and files[0]["channel"] == "alpha"


def test_live_dce_missing_clean_error():
    from app.calliope_shell import discord_live
    import unittest.mock as mock

    c = _client(tempfile.mkstemp(suffix=".db")[1])
    with mock.patch.object(discord_live, "dce_available", return_value=False):
        r = c.post("/api/import/discord/live", json={"channel_ids": ["111"]})
    assert r.status_code == 503
    body = r.get_json()
    assert body["dce_available"] is False
    assert "dce" in body["error"].lower()
