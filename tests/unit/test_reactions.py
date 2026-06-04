import sqlite3
import tempfile
from pathlib import Path

import pytest

# Importiamo le funzioni dal modulo appena riscritto
from app.db.reactions import add_reaction, list_reactions
# Importiamo le utility di inizializzazione schema
import app.db as db_mod


@pytest.fixture
def db_connection():
    """
    Fixture pytest che crea un database SQLite temporaneo,
    inizializza lo schema reale e lo chiude al termine del test.
    """
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        db_path = Path(tf.name)

    conn = sqlite3.connect(str(db_path))
    try:
        # Inizializza lo schema completo (include scene_reactions)
        db_mod.init_schema(conn)

        # Inseriamo record reali nelle tabelle di base.
        cur = conn.cursor()

        # Creiamo una scena
        scene_id = db_mod.new_id() if hasattr(db_mod, "new_id") else None
        if scene_id is not None:
            cur.execute("INSERT INTO scenes (id) VALUES (?)", (scene_id,))
        else:
            cur.execute("INSERT INTO scenes DEFAULT VALUES")
            scene_id = cur.lastrowid

        # Creiamo un personaggio associato alla scena
        character_id = db_mod.new_id() if hasattr(db_mod, "new_id") else None
        if character_id is not None:
            cur.execute(
                "INSERT INTO characters (id, scene_id) VALUES (?, ?)",
                (character_id, scene_id),
            )
        else:
            cur.execute(
                "INSERT INTO characters (scene_id) VALUES (?)",
                (scene_id,),
            )
            character_id = cur.lastrowid

        # Creiamo un messaggio associato a scena e personaggio
        message_id = db_mod.new_id() if hasattr(db_mod, "new_id") else None
        if message_id is not None:
            cur.execute(
                "INSERT INTO messages (id, scene_id, character_id, content) VALUES (?, ?, ?, ?)",
                (message_id, scene_id, character_id, "Ciao mondo"),
            )
        else:
            cur.execute(
                "INSERT INTO messages (scene_id, character_id, content) VALUES (?, ?, ?)",
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
        message_id=message_id,
        character_id=character_id,
        emoji="👍",
    )
    assert isinstance(reaction_id, int)

    # Recuperiamo le reazioni filtrando per il messaggio appena creato
    reactions = list_reactions(conn, message_id=message_id)

    # Dovremmo ottenere esattamente una reazione con i dati inseriti
    assert len(reactions) == 1
    reaction = reactions[0]

    # Verifichiamo i campi chiave
    assert reaction["id"] == reaction_id
    assert reaction["scene_id"] == scene_id
    assert reaction["character_id"] == character_id
    assert reaction["message_id"] == message_id
    assert reaction["reaction"] == "👍"
