import tempfile
import sqlite3
from app.db import init_schema
def test_migration_characters_structure():
    """Verifica la struttura della tabella characters."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tf:
        conn = sqlite3.connect(tf.name)
        init_schema(conn)

        # Verifica struttura tabella characters
        cursor = conn.execute("PRAGMA table_info(characters)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert "id" in columns
        assert columns["id"] == "TEXT"
        assert "name" in columns
        assert columns["name"] == "TEXT"
        assert "description" in columns
        assert columns["description"] == "TEXT"
        assert "avatar_url" in columns
        assert columns["avatar_url"] == "TEXT"
        assert "created_at" in columns
        assert columns["created_at"] == "TEXT"
