import tempfile
import sqlite3
from app.db import init_schema
def test_migration_scene_messages_structure():
    """Verifica la struttura della tabella scene_messages."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tf:
        conn = sqlite3.connect(tf.name)
        init_schema(conn)

        # Verifica struttura tabella scene_messages
        cursor = conn.execute("PRAGMA table_info(scene_messages)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert "id" in columns
        assert columns["id"] == "TEXT"
        assert "scene_id" in columns
        assert columns["scene_id"] == "TEXT"
        assert "message_id" in columns
        assert columns["message_id"] == "TEXT"
        assert "position" in columns
        assert columns["position"] == "INTEGER"
