import sqlite3
import tempfile

from app.db import init_schema


def test_schema_migrations():
    """
    Verifica che lo script di migrazione crei tutte le tabelle previste.
    """
    # Creiamo un database SQLite temporaneo
    with tempfile.NamedTemporaryFile(suffix=".db") as tf:
        conn = sqlite3.connect(tf.name)

        # Eseguiamo le migrazioni
        init_schema(conn)

        # Recuperiamo l'elenco delle tabelle presenti
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}

        # Elenco delle tabelle che ci aspettiamo siano state create
        expected_tables = {
            "arcs",
            "scenes",
            "characters",
            "scene_characters",
            "messages",
            "lore_entries",
            "arc_lore",
            "scene_reactions",
        }

        missing = expected_tables - tables
        assert not missing, f"Tabelle mancanti dopo le migrazioni: {missing}"
