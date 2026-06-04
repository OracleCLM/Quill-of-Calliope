import pytest

from app.db.messages import (
    Base,
    SessionLocal,
    engine,
    Scene,
    Character,
    add_message,
    list_messages_for_scene,
    count_messages_for_scene,
    get_message_by_id,
)


@pytest.fixture(scope="module", autouse=True)
def setup_schema():
    """
    Crea lo schema del database una sola volta per il modulo di test.
    """
    Base.metadata.create_all(engine)
    yield
    # (non è necessario fare teardown per un DB in‑memory)


def test_add_and_list_messages_order():
    """
    Verifica che ``list_messages_for_scene`` restituisca i messaggi ordinati
    correttamente in base a ``position_order``.
    """
    session = SessionLocal()

    # Creazione di una scena e di un personaggio di prova
    scene = Scene(name="TestScene")
    character = Character(name="TestChar")
    session.add_all([scene, character])
    session.commit()

    # Inserimento di due messaggi con ordine diverso
    add_message(
        session,
        scene_id=scene.id,
        character_id=character.id,
        content="Primo messaggio (ordine 2)",
        position_order=2,
    )
    add_message(
        session,
        scene_id=scene.id,
        character_id=character.id,
        content="Secondo messaggio (ordine 1)",
        position_order=1,
    )

    # Recupero e verifica dell'ordine
    msgs = list_messages_for_scene(session, scene.id)
    assert [m.content for m in msgs] == [
        "Secondo messaggio (ordine 1)",
        "Primo messaggio (ordine 2)",
    ]

    session.close()

def test_count_messages_for_scene():
    """
    Verifica che ``count_messages_for_scene`` restituisca il numero corretto di messaggi.
    """
    session = SessionLocal()

    # Creazione di una scena e di un personaggio di prova
    scene = Scene(name="TestScene")
    character = Character(name="TestChar")
    session.add_all([scene, character])
    session.commit()

    # Inserimento di due messaggi
    add_message(
        session,
        scene_id=scene.id,
        character_id=character.id,
        content="Primo messaggio",
        position_order=1,
    )
    add_message(
        session,
        scene_id=scene.id,
        character_id=character.id,
        content="Secondo messaggio",
        position_order=2,
    )

    # Verifica del conteggio dei messaggi
    assert count_messages_for_scene(session, scene.id) == 2

    # Verifica del conteggio dei messaggi per una scena vuota
    empty_scene = Scene(name="EmptyScene")
    session.add(empty_scene)
    session.commit()
    assert count_messages_for_scene(session, empty_scene.id) == 0

    session.close()

def test_get_message_by_id():
    """
    Verifica che ``get_message_by_id`` restituisca il messaggio corretto o None se non trovato.
    """
    session = SessionLocal()

    # Creazione di una scena e di un personaggio di prova
    scene = Scene(name="TestScene")
    character = Character(name="TestChar")
    session.add_all([scene, character])
    session.commit()

    # Inserimento di un messaggio
    msg_id = add_message(
        session,
        scene_id=scene.id,
        character_id=character.id,
        content="Test messaggio",
        position_order=1,
    )

    # Verifica del recupero del messaggio
    msg = get_message_by_id(session, msg_id)
    assert msg is not None
    assert msg.content == "Test messaggio"

    # Verifica del recupero di un messaggio non esistente
    assert get_message_by_id(session, "non-existent-id") is None

    session.close()
