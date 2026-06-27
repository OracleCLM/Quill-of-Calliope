"""
CONTRACT WI-REACT-DEDUP: add_reaction deve essere idempotente su (message_id, character_id, emoji).
Due chiamate identiche → una sola riga in list_reactions.
"""
import tempfile
from pathlib import Path
import sqlite3

import app.db as db_mod
from app.db.reactions import add_reaction, list_reactions


def _make_db():
    tf = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tf.close()
    conn = sqlite3.connect(tf.name)
    conn.row_factory = sqlite3.Row
    db_mod.init_schema(conn)

    scene_id = db_mod.new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "Dedup Scene"))

    char_id = db_mod.new_id()
    conn.execute("INSERT INTO characters (id, name) VALUES (?, ?)", (char_id, "Dedup Char"))

    msg_id = db_mod.new_id()
    conn.execute(
        "INSERT INTO messages (id, scene_id, character_id, content_original, ts) VALUES (?, ?, ?, ?, ?)",
        (msg_id, scene_id, char_id, "Testo di test", "2026-06-15T00:00:00Z"),
    )
    conn.commit()
    return conn, Path(tf.name), char_id, msg_id


def test_add_reaction_idempotent_same_emoji():
    """Due add_reaction identici → una sola riga in list_reactions."""
    conn, db_path, char_id, msg_id = _make_db()
    try:
        add_reaction(conn, message_id=msg_id, character_id=char_id, emoji="👍")
        add_reaction(conn, message_id=msg_id, character_id=char_id, emoji="👍")

        reactions = list_reactions(conn, message_id=msg_id)
        assert len(reactions) == 1, f"Attesa 1 reaction, trovate {len(reactions)}"
        assert reactions[0]["emoji"] == "👍"
        assert reactions[0]["character_id"] == char_id
        assert reactions[0]["message_id"] == msg_id
    finally:
        conn.close()
        db_path.unlink(missing_ok=True)


def test_add_reaction_different_emoji_not_deduped():
    """Emoji diverse dallo stesso personaggio sullo stesso msg restano distinte."""
    conn, db_path, char_id, msg_id = _make_db()
    try:
        add_reaction(conn, message_id=msg_id, character_id=char_id, emoji="👍")
        add_reaction(conn, message_id=msg_id, character_id=char_id, emoji="❤️")

        reactions = list_reactions(conn, message_id=msg_id)
        assert len(reactions) == 2
    finally:
        conn.close()
        db_path.unlink(missing_ok=True)
