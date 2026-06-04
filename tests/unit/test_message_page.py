import pytest

from app.db.messages import (
    Base,
    SessionLocal,
    engine,
    Scene,
    Character,
    add_message,
    get_scene_message_page,
)


@pytest.fixture(scope="module", autouse=True)
def setup_schema():
    """Crea lo schema una sola volta per il modulo (DB in-memory)."""
    Base.metadata.create_all(engine)
    yield


def _seed_scene(session, n=5):
    """Crea una scena + personaggio e inserisce n messaggi position_order 0..n-1."""
    scene = Scene(name="PageScene")
    character = Character(name="PageChar")
    session.add_all([scene, character])
    session.commit()
    for i in range(n):
        add_message(
            session,
            scene_id=scene.id,
            character_id=character.id,
            content=f"msg-{i}",
            position_order=i,
        )
    return scene.id


def test_first_page_has_more():
    """Prima pagina (limit=2, offset=0): total=5, 2 messaggi, has_more True, ordinati."""
    session = SessionLocal()
    scene_id = _seed_scene(session, n=5)

    page = get_scene_message_page(session, scene_id, limit=2, offset=0)
    assert page["total"] == 5
    assert page["limit"] == 2
    assert page["offset"] == 0
    assert len(page["messages"]) == 2
    assert page["has_more"] is True
    assert [m.content for m in page["messages"]] == ["msg-0", "msg-1"]

    session.close()


def test_last_page_no_more():
    """Ultima pagina (limit=2, offset=4): 1 messaggio residuo, has_more False."""
    session = SessionLocal()
    scene_id = _seed_scene(session, n=5)

    page = get_scene_message_page(session, scene_id, limit=2, offset=4)
    assert page["total"] == 5
    assert len(page["messages"]) == 1
    assert page["has_more"] is False
    assert page["messages"][0].content == "msg-4"

    session.close()
