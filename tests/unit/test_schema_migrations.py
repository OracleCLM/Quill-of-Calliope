import tempfile
import sqlite3
from app.db import init_schema
def test_migration_scene_characters_structure():
    """Verifica la struttura della tabella scene_characters."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tf:
        conn = sqlite3.connect(tf.name)
        init_schema(conn)

        # Verifica struttura tabella scene_characters
        cursor = conn.execute("PRAGMA table_info(scene_characters)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert "scene_id" in columns
        assert columns["scene_id"] == "TEXT"
        assert "character_id" in columns
        assert columns["character_id"] == "TEXT"
        assert "position" in columns
        assert columns["position"] == "INTEGER"
