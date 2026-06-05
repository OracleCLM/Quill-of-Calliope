import pytest
from sqlalchemy.orm import Session

from app.db.messages import (
    Base,
    SessionLocal,
    engine,
    Scene,
    Character,
    Message,
    insert_message_at,
    list_messages_for_scene,
)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_insert_message_at_shifts_existing(db_session: Session):
    # Setup: Crea Scene e Character
    scene = Scene(name="Test Scene")
    db_session.add(scene)
    db_session.flush()

    character = Character(name="Test Character")
    db_session.add(character)
    db_session.flush()

    # Setup: Inserisci 3 messaggi A, B, C con position_order 1, 2, 3
    msg_a = Message(
        scene_id=scene.id,
        character_id=character.id,
        content="A",
        position_order=1,
    )
    msg_b = Message(
        scene_id=scene.id,
        character_id=character.id,
        content="B",
        position_order=2,
    )
    msg_c = Message(
        scene_id=scene.id,
        character_id=character.id,
        content="C",
        position_order=3,
    )
    db_session.add_all([msg_a, msg_b, msg_c])
    db_session.commit()

    # Action: Inserisci X alla posizione 2
    insert_message_at(
        db_session,
        scene_id=scene.id,
        character_id=character.id,
        content="X",
        position=2,
    )

    # Assertion: Verifica ordine contenuti e position_order
    messages = list_messages_for_scene(db_session, scene.id)
    contents = [m.content for m in messages]
    positions = [m.position_order for m in messages]

    assert contents == ["A", "X", "B", "C"]
    assert positions == [1, 2, 3, 4]
