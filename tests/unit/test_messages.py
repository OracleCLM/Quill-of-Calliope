import pytest

from app.db.messages import (
    Base,
    SessionLocal,
    engine,
    Scene,
    Character,
    add_message,
    list_messages_for_scene,
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
