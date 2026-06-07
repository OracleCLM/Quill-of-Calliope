import tempfile
import sqlite3
from app.db import init_schema
def test_migration_table_structure():
    """Verifica la struttura delle tabelle create dalle migrazioni."""
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

        # Verifica struttura tabella scenes
        cursor = conn.execute("PRAGMA table_info(scenes)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert "id" in columns
        assert columns["id"] == "TEXT"
        assert "arc_id" in columns
        assert columns["arc_id"] == "TEXT"
