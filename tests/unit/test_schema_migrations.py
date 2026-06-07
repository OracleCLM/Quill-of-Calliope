import tempfile
import sqlite3
from app.db import init_schema
def test_migration_foreign_keys():
    """Verifica che le foreign keys siano abilitate."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tf:
        conn = sqlite3.connect(tf.name)
        init_schema(conn)

        # Verifica che le foreign keys siano abilitate
        cursor = conn.execute("PRAGMA foreign_keys")
        assert cursor.fetchone()[0] == 1

def test_migration_journal_mode():
    """Verifica che il journal mode sia WAL."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tf:
        conn = sqlite3.connect(tf.name)
        init_schema(conn)

        # Verifica che il journal mode sia WAL
        cursor = conn.execute("PRAGMA journal_mode")
        assert cursor.fetchone()[0] == "wal"
