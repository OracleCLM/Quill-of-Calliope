"""Test unit per scripts/discord_jsonl_to_db.py.

Verifica le funzioni pure (channel_scene_title, dedup_key) e il run() end-to-end
con un JSONL minimale e un DB temporaneo.
"""
from __future__ import annotations

import json

import pytest

from app.db import get_db, init_schema
from scripts.discord_jsonl_to_db import (
    DISCORD_SCENE_PREFIX,
    _channel_scene_title,
    _dedup_key,
    _get_or_create_scene,
    run,
)


@pytest.fixture
def db(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    conn.close()
    return p


@pytest.fixture
def jsonl(tmp_path):
    records = [
        {"channel_id": "111", "channel_name": "rp-main", "timestamp": "2026-01-01T10:00:00Z",
         "author_name": "Alice", "content": "Hello world", "tag": "IC"},
        {"channel_id": "111", "channel_name": "rp-main", "timestamp": "2026-01-01T10:01:00Z",
         "author_name": "Bob", "content": "Hi there", "tag": "IC"},
        {"channel_id": "222", "channel_name": "ooc-chat", "timestamp": "2026-01-01T10:02:00Z",
         "author_name": "Alice", "content": "OOC comment", "tag": "OOC"},
    ]
    p = tmp_path / "messages.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    return p


# --- pure functions ---

def test_channel_scene_title():
    assert _channel_scene_title("rp-main") == "[Discord] #rp-main"


def test_dedup_key_deterministic():
    rec = {"channel_id": "111", "timestamp": "T", "author_name": "Alice"}
    assert _dedup_key(rec) == _dedup_key(rec)


def test_dedup_key_differs_on_ts():
    r1 = {"channel_id": "111", "timestamp": "T1", "author_name": "Alice"}
    r2 = {"channel_id": "111", "timestamp": "T2", "author_name": "Alice"}
    assert _dedup_key(r1) != _dedup_key(r2)


def test_discord_scene_prefix_constant():
    assert DISCORD_SCENE_PREFIX == "discord_channel__"


# --- _get_or_create_scene ---

def test_get_or_create_scene_creates_new(db):
    conn = get_db(db)
    sid = _get_or_create_scene(conn, "111", "rp-main", dry_run=False)
    assert sid == f"{DISCORD_SCENE_PREFIX}111"
    row = conn.execute("SELECT title, is_readonly FROM scenes WHERE id = ?", (sid,)).fetchone()
    assert row["title"] == "[Discord] #rp-main"
    assert row["is_readonly"] == 1
    conn.close()


def test_get_or_create_scene_idempotent(db):
    conn = get_db(db)
    s1 = _get_or_create_scene(conn, "111", "rp-main", dry_run=False)
    s2 = _get_or_create_scene(conn, "111", "rp-main", dry_run=False)
    assert s1 == s2
    count = conn.execute("SELECT COUNT(*) FROM scenes WHERE id = ?", (s1,)).fetchone()[0]
    assert count == 1
    conn.close()


def test_get_or_create_scene_dry_run_no_insert(db):
    conn = get_db(db)
    _get_or_create_scene(conn, "999", "test-ch", dry_run=True)
    count = conn.execute("SELECT COUNT(*) FROM scenes WHERE id LIKE '%999%'").fetchone()[0]
    assert count == 0
    conn.close()


# --- run() integration ---

def test_run_inserts_ic_messages(db, jsonl, monkeypatch):
    monkeypatch.setenv("CALLIOPE_DB_PATH", str(db))
    import scripts.discord_jsonl_to_db as m
    original_get_db = m.get_db
    m.get_db = lambda *a, **kw: get_db(db)
    try:
        stats = run(jsonl, dry_run=False, only_ic=True, limit=None)
    finally:
        m.get_db = original_get_db
    assert stats["inserted"] == 2
    assert stats["skipped_tag"] == 1


def test_run_dry_run_no_real_inserts(db, jsonl):
    """dry_run=True conta gli inserimenti potenziali ma non scrive nel DB."""
    import scripts.discord_jsonl_to_db as m
    m.get_db = lambda *a, **kw: get_db(db)
    try:
        run(jsonl, dry_run=True, only_ic=True, limit=None)
    finally:
        import importlib
        importlib.reload(m)
    conn = get_db(db)
    n = conn.execute("SELECT COUNT(*) FROM messages WHERE source='discord'").fetchone()[0]
    conn.close()
    assert n == 0, "dry_run non deve inserire righe reali nel DB"


def test_run_idempotent(db, jsonl, monkeypatch):
    import scripts.discord_jsonl_to_db as m
    m.get_db = lambda *a, **kw: get_db(db)
    try:
        r1 = run(jsonl, dry_run=False, only_ic=True, limit=None)
        r2 = run(jsonl, dry_run=False, only_ic=True, limit=None)
    finally:
        import importlib
        importlib.reload(m)
    assert r1["inserted"] == 2
    assert r2["inserted"] == 0
    assert r2["skipped_dedup"] == 2
