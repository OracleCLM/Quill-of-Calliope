import tempfile
from pathlib import Path
import sqlite3

import app.db as db_mod
from app.db.reactions import add_reaction, list_reactions


def _make_db():
    tf = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tf.close()
    conn = sqlite3.connect(tf.name)
    db_mod.init_schema(conn)

    cur = conn.cursor()

    scene_id = db_mod.new_id()
    cur.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "Test Scene"))

    char_id = db_mod.new_id()
    cur.execute("INSERT INTO characters (id, name) VALUES (?, ?)", (char_id, "Test Char"))

    msg_id = db_mod.new_id()
    cur.execute(
        "INSERT INTO messages (id, scene_id, character_id, content_original, ts) VALUES (?, ?, ?, ?, ?)",
        (msg_id, scene_id, char_id, "Ciao mondo", "2026-01-01T00:00:00Z"),
    )
    conn.commit()
    return conn, Path(tf.name), char_id, msg_id


def test_add_and_list_reaction():
    conn, db_path, char_id, msg_id = _make_db()
    try:
        reaction_id = add_reaction(conn, message_id=msg_id, character_id=char_id, emoji="👍")

        assert isinstance(reaction_id, str)

        reactions = list_reactions(conn, message_id=msg_id)
        assert len(reactions) == 1
        r = reactions[0]
        assert r["id"] == reaction_id
        assert r["message_id"] == msg_id
        assert r["character_id"] == char_id
        assert r["emoji"] == "👍"
    finally:
        conn.close()
        db_path.unlink(missing_ok=True)


def test_list_reactions_empty_message():
    """list_reactions su messaggio senza reazioni restituisce lista vuota."""
    conn, db_path, char_id, msg_id = _make_db()
    try:
        reactions = list_reactions(conn, message_id=msg_id)
        assert reactions == []
    finally:
        conn.close()
        db_path.unlink(missing_ok=True)


def test_add_multiple_reactions():
    """Più reazioni sullo stesso messaggio sono tutte restituite."""
    conn, db_path, char_id, msg_id = _make_db()
    try:
        add_reaction(conn, message_id=msg_id, character_id=char_id, emoji="👍")
        add_reaction(conn, message_id=msg_id, character_id=char_id, emoji="❤️")

        reactions = list_reactions(conn, message_id=msg_id)
        assert len(reactions) == 2
        emojis = {r["emoji"] for r in reactions}
        assert "👍" in emojis
        assert "❤️" in emojis
    finally:
        conn.close()
        db_path.unlink(missing_ok=True)


def test_add_reaction_with_empty_emoji():
    """add_reaction con emoji vuota inserisce correttamente."""
    conn, db_path, char_id, msg_id = _make_db()
    try:
        reaction_id = add_reaction(conn, message_id=msg_id, character_id=char_id, emoji="")

        assert isinstance(reaction_id, str)

        reactions = list_reactions(conn, message_id=msg_id)
        assert len(reactions) == 1
        r = reactions[0]
        assert r["id"] == reaction_id
        assert r["message_id"] == msg_id
        assert r["character_id"] == char_id
        assert r["emoji"] == ""
    finally:
        conn.close()
        db_path.unlink(missing_ok=True)
