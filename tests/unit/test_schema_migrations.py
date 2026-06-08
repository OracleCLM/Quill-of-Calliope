import tempfile
import sqlite3
from app.db import init_schema
def test_migration_scene_reactions_structure():
    """Verifica la struttura della tabella scene_reactions."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tf:
        conn = sqlite3.connect(tf.name)
        init_schema(conn)

        # Verifica struttura tabella scene_reactions
        cursor = conn.execute("PRAGMA table_info(scene_reactions)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert "id" in columns
        assert columns["id"] == "TEXT"
        assert "scene_id" in columns
        assert columns["scene_id"] == "TEXT"
        assert "character_id" in columns
        assert columns["character_id"] == "TEXT"
        assert "emoji" in columns
        assert columns["emoji"] == "TEXT"
        assert "message_id" in columns
        assert columns["message_id"] == "TEXT"
