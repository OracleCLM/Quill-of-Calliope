import pytest

from app.db.messages import (
    Base,
    SessionLocal,
    engine,
    Scene,
    Character,
    add_message,
    get_message_by_id,
    count_messages_for_scene,
    delete_message,
)


@pytest.fixture(scope="module", autouse=True)
def setup_schema():
    """Crea lo schema una sola volta per il modulo (DB in-memory)."""
    Base.metadata.create_all(engine)
    yield


def test_delete_existing_message():
    """delete_message su id esistente: True, riga rimossa, count decrementato."""
    session = SessionLocal()
    scene = Scene(name="DelScene")
    character = Character(name="DelChar")
    session.add_all([scene, character])
    session.commit()

    msg_id = add_message(
        session,
        scene_id=scene.id,
        character_id=character.id,
        content="to delete",
        position_order=0,
    )
    assert count_messages_for_scene(session, scene.id) == 1

    assert delete_message(session, msg_id) is True
    assert get_message_by_id(session, msg_id) is None
    assert count_messages_for_scene(session, scene.id) == 0

    session.close()


def test_delete_missing_message():
    """delete_message su id inesistente: False (nessun errore)."""
    session = SessionLocal()
    assert delete_message(session, "non-existent-id") is False
    session.close()
