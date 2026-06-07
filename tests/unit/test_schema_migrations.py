import tempfile
import sqlite3
from app.db import init_schema
def test_migration_lore_entries_structure():
    """Verifica la struttura della tabella lore_entries."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tf:
        conn = sqlite3.connect(tf.name)
        init_schema(conn)

        # Verifica struttura tabella lore_entries
        cursor = conn.execute("PRAGMA table_info(lore_entries)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert "id" in columns
        assert columns["id"] == "TEXT"
        assert "title" in columns
        assert columns["title"] == "TEXT"
        assert "content_text" in columns
        assert columns["content_text"] == "TEXT"
        assert "category" in columns
        assert columns["category"] == "TEXT"
