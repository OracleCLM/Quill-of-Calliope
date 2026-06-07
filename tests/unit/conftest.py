"""Fixtures condivise per i test di app/db/messages.py (sqlite3 raw)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.db import new_id

_MIGRATION = Path(__file__).parents[2] / "app" / "db" / "migrations" / "001_scene_as_chat.sql"


@pytest.fixture
def msg_conn():
    """In-memory SQLite con schema completo per test messages."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(_MIGRATION.read_text())
    yield c
    c.close()


def add_scene(conn: sqlite3.Connection, title: str = "TestScene") -> str:
    sid = new_id()
    conn.execute(
        "INSERT INTO scenes(id,title,created_at,updated_at) VALUES(?,?,datetime('now'),datetime('now'))",
        (sid, title),
    )
    conn.commit()
    return sid


def add_character(conn: sqlite3.Connection, name: str = "TestChar") -> str:
    cid = new_id()
    conn.execute(
        "INSERT INTO characters(id,name,created_at,updated_at) VALUES(?,?,datetime('now'),datetime('now'))",
        (cid, name),
    )
    conn.commit()
    return cid
