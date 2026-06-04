import sqlite3
import tempfile
from pathlib import Path

import pytest

# Importiamo le funzioni dal modulo appena creato
from app.db.reactions import init_db, add_reaction, list_reactions


@pytest.fixture
def db_connection():
    """
    Fixture pytest che crea un database SQLite temporaneo,
    inizializza le tabelle e lo chiude al termine del test.
    """
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        db_path = Path(tf.name)
    conn = sqlite3.connect(str(db_path))
    try:
        init_db(conn)

        # Inseriamo dati di base: una scena, un personaggio e un messaggio.
        cur = conn.cursor()
        cur.execute("INSERT INTO scenes DEFAULT VALUES")
        scene_id = cur.lastrowid

        cur.execute(
            "INSERT INTO characters (scene_id) VALUES (?)",
            (scene_id,),
        )
        character_id = cur.lastrowid

        cur.execute(
            "INSERT INTO messages (scene_id, character_id, content) VALUES (?,?,?)",
            (scene_id, character_id, "Ciao mondo"),
        )
        message_id = cur.lastrowid

        conn.commit()

        # Passiamo gli ID tramite attributi della fixture per usarli nei test.
        yield {
            "conn": conn,
            "scene_id": scene_id,
            "character_id": character_id,
            "message_id": message_id,
        }
    finally:
        conn.close()
        db_path.unlink(missing_ok=True)


def test_add_and_list_reaction(db_connection):
    conn = db_connection["conn"]
    scene_id = db_connection["scene_id"]
    character_id = db_connection["character_id"]
    message_id = db_connection["message_id"]

    # Aggiungiamo una reazione
    reaction_id = add_reaction(
        conn,
        scene_id=scene_id,
        character_id=character_id,
        message_id=message_id,
        reaction="👍",
    )
    assert isinstance(reaction_id, int)

    # Recuperiamo le reazioni filtrando per la scena appena creata
    reactions = list_reactions(conn, scene_id=scene_id)

    # Dovremmo ottenere esattamente una reazione con i dati inseriti
    assert len(reactions) == 1
    reaction = reactions[0]
    assert reaction["id"] == reaction_id
    assert reaction["scene_id"] == scene_id
    assert reaction["character_id"] == character_id
    assert reaction["message_id"] == message_id
    assert reaction["reaction"] == "👍"
