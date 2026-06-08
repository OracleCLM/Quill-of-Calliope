import tempfile
import sqlite3
from app.db import init_schema
def test_migration_scene_arcs_structure():
    """Verifica la struttura della tabella scene_arcs."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tf:
        conn = sqlite3.connect(tf.name)
        init_schema(conn)

        # Verifica struttura tabella scene_arcs
        cursor = conn.execute("PRAGMA table_info(scene_arcs)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert "id" in columns
        assert columns["id"] == "TEXT"
        assert "scene_id" in columns
        assert columns["scene_id"] == "TEXT"
        assert "arc_id" in columns
        assert columns["arc_id"] == "TEXT"
        assert "position" in columns
        assert columns["position"] == "INTEGER"
