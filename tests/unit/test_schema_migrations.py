import tempfile
import sqlite3
from app.db import init_schema
def test_migration_scene_lore_structure():
    """Verifica la struttura della tabella scene_lore."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tf:
        conn = sqlite3.connect(tf.name)
        init_schema(conn)

        # Verifica struttura tabella scene_lore
        cursor = conn.execute("PRAGMA table_info(scene_lore)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert "id" in columns
        assert columns["id"] == "TEXT"
        assert "scene_id" in columns
        assert columns["scene_id"] == "TEXT"
        assert "lore_id" in columns
        assert columns["lore_id"] == "TEXT"
        assert "position" in columns
        assert columns["position"] == "INTEGER"
