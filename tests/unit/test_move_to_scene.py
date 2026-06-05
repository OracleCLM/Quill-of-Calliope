import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.messages import (
    Base,
    Scene,
    Character,
    add_message,
    list_messages_for_scene,
    count_messages_for_scene,
    move_message_to_scene,
)

def test_move_message_to_scene():
    # Setup DB
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session = Session(engine)

    # Create Data
    scene_a = Scene(id="scene_a", name="Scene A")
    scene_b = Scene(id="scene_b", name="Scene B")
    char_c = Character(id="char_c", name="Char C")
    session.add_all([scene_a, scene_b, char_c])
    session.commit()

    # Populate A
    add_message(session, "scene_a", "char_c", "A1", 1)
    id_a2 = add_message(session, "scene_a", "char_c", "A2", 2)
    add_message(session, "scene_a", "char_c", "A3", 3)

    # Populate B
    add_message(session, "scene_b", "char_c", "B1", 1)
    add_message(session, "scene_b", "char_c", "B2", 2)

    # Execute Move
    result = move_message_to_scene(session, id_a2, "scene_b", 2)
    assert result is True

    # Verify B
    msgs_b = list_messages_for_scene(session, "scene_b")
    assert len(msgs_b) == 3
    assert [m.content for m in msgs_b] == ["B1", "A2", "B2"]
    assert [m.position_order for m in msgs_b] == [1, 2, 3]

    # Verify A
    msgs_a = list_messages_for_scene(session, "scene_a")
    assert len(msgs_a) == 2
    assert [m.content for m in msgs_a] == ["A1", "A3"]
    assert [m.position_order for m in msgs_a] == [1, 2]

    # Test Non-existent
    count_b_before = count_messages_for_scene(session, "scene_b")
    result_false = move_message_to_scene(session, "non_existent", "scene_b", 1)
    assert result_false is False
    assert count_messages_for_scene(session, "scene_b") == count_b_before

    print("All tests passed.")

if __name__ == "__main__":
    test_move_message_to_scene()
