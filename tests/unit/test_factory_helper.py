"""Test del factory helper parent-row su schema reale (init_schema, FK ON)."""

import sqlite3

from app.db import init_schema
from tests.helpers.factory import make_character, make_message, make_scene


def _temp_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    init_schema(conn)
    return conn


def test_factory_creates_valid_parent_rows():
    conn = _temp_conn()

    scene_id = make_scene(conn, title="La Taverna")
    char_id = make_character(conn, name="Calliope", kind="npc")
    msg_id = make_message(
        conn,
        scene_id,
        character_id=char_id,
        content_original="ciao",
    )

    scene = conn.execute(
        "SELECT id, title FROM scenes WHERE id = ?", (scene_id,)
    ).fetchone()
    assert scene is not None
    assert scene["title"] == "La Taverna"

    char = conn.execute(
        "SELECT id, name, kind FROM characters WHERE id = ?", (char_id,)
    ).fetchone()
    assert char is not None
    assert char["name"] == "Calliope"
    assert char["kind"] == "npc"

    msg = conn.execute(
        "SELECT id, scene_id, character_id, content_original, ts, source "
        "FROM messages WHERE id = ?",
        (msg_id,),
    ).fetchone()
    assert msg is not None
    assert msg["scene_id"] == scene_id
    assert msg["character_id"] == char_id
    assert msg["content_original"] == "ciao"
    assert msg["ts"] == "2026-01-01T00:00:00Z"
    assert msg["source"] == "manual"

    conn.close()


def test_message_foreign_keys_hold():
    """Una scene_id inesistente deve violare la FK (foreign_keys ON)."""
    conn = _temp_conn()

    try:
        conn.execute("INSERT INTO messages (id, scene_id, ts) VALUES (?, ?, ?)",
                     ("orphan", "no-such-scene", "2026-01-01T00:00:00Z"))
        conn.commit()
        raised = False
    except sqlite3.IntegrityError:
        raised = True

    assert raised, "FK su scene_id inesistente deve sollevare IntegrityError"
    conn.close()


def test_message_character_id_nullable():
    """character_id è nullable: un messaggio senza character deve passare."""
    conn = _temp_conn()
    scene_id = make_scene(conn)
    msg_id = make_message(conn, scene_id)

    msg = conn.execute(
        "SELECT character_id FROM messages WHERE id = ?", (msg_id,)
    ).fetchone()
    assert msg is not None
    assert msg["character_id"] is None
    conn.close()
