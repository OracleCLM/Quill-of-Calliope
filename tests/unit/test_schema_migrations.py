import tempfile
import sqlite3
from app.db import init_schema
def test_migration_arcs_structure():
    """Verifica la struttura della tabella arcs."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tf:
        conn = sqlite3.connect(tf.name)
        init_schema(conn)

        # Verifica struttura tabella arcs
        cursor = conn.execute("PRAGMA table_info(arcs)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert "id" in columns
        assert columns["id"] == "TEXT"
        assert "title" in columns
        assert columns["title"] == "TEXT"
        assert "description" in columns
        assert columns["description"] == "TEXT"
        assert "created_at" in columns
        assert columns["created_at"] == "TEXT"
        assert "updated_at" in columns
        assert columns["updated_at"] == "TEXT"
