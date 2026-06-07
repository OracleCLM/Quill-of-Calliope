import tempfile
import sqlite3
from app.db import init_schema
def test_migration_arc_lore_structure():
    """Verifica la struttura della tabella arc_lore."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tf:
        conn = sqlite3.connect(tf.name)
        init_schema(conn)

        # Verifica struttura tabella arc_lore
        cursor = conn.execute("PRAGMA table_info(arc_lore)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert "arc_id" in columns
        assert columns["arc_id"] == "TEXT"
        assert "lore_id" in columns
        assert columns["lore_id"] == "TEXT"
