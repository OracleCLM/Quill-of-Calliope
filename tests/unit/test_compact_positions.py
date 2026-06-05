import pytest
from sqlalchemy.orm import Session

from app.db.messages import (
    Base,
    SessionLocal,
    Scene,
    Character,
    add_message,
    compact_scene_positions,
    list_messages_for_scene,
    engine,
)


@pytest.fixture(scope="function")
def db_session() -> Session:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_compact_positions_removes_gaps(db_session: Session) -> None:
    # Setup: 1 Scene, 1 Character
    scene = Scene(name="Test Scene")
    db_session.add(scene)
    db_session.commit()

    character = Character(name="Test Character")
    db_session.add(character)
    db_session.commit()

    # Setup: 3 Messages con buchi (1, 3, 7)
    add_message(db_session, scene.id, character.id, "A", 1)
    add_message(db_session, scene.id, character.id, "B", 3)
    add_message(db_session, scene.id, character.id, "C", 7)

    # Action
    result = compact_scene_positions(db_session, scene.id)

    # Assertions
    assert result == 3

    messages = list_messages_for_scene(db_session, scene.id)
    assert len(messages) == 3

    # Verifica ordine e contenuto
    assert messages[0].content == "A"
    assert messages[1].content == "B"
    assert messages[2].content == "C"

    # Verifica posizioni contigue
    assert messages[0].position_order == 1
    assert messages[1].position_order == 2
    assert messages[2].position_order == 3
