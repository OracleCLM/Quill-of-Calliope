import tempfile
import sqlite3
from app.db import init_schema
def test_migration_messages_structure():
    """Verifica la struttura della tabella messages."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tf:
        conn = sqlite3.connect(tf.name)
        init_schema(conn)

        # Verifica struttura tabella messages
        cursor = conn.execute("PRAGMA table_info(messages)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert "id" in columns
        assert columns["id"] == "TEXT"
        assert "scene_id" in columns
        assert columns["scene_id"] == "TEXT"
        assert "character_id" in columns
        assert columns["character_id"] == "TEXT"
        assert "content" in columns
        assert columns["content"] == "TEXT"
        assert "timestamp" in columns
        assert columns["timestamp"] == "TEXT"
