

from app.db.messages import (
    Base,
    Scene,
    Character,
    engine,
    SessionLocal,
    merge_scenes,
    list_messages_for_scene,
    add_message,
    count_messages_for_scene,
)


def test_merge_scenes_basic():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    char = Character(name="TestChar")
    session.add(char)
    session.flush()

    scene_a = Scene(name="Scene A")
    session.add(scene_a)
    session.flush()

    scene_b = Scene(name="Scene B")
    session.add(scene_b)
    session.flush()

    id_a1 = add_message(session, scene_a.id, char.id, "A1", 1)
    id_a2 = add_message(session, scene_a.id, char.id, "A2", 2)

    id_b1 = add_message(session, scene_b.id, char.id, "B1", 1)

    new_scene_id = merge_scenes(session, scene_a.id, scene_b.id, "Merged")

    new_scene = session.get(Scene, new_scene_id)
    assert new_scene is not None
    assert new_scene.name == "Merged"

    merged_msgs = list_messages_for_scene(session, new_scene_id)
    assert len(merged_msgs) == 3

    contents = [m.content for m in merged_msgs]
    assert contents == ["A1", "A2", "B1"]

    positions = [m.position_order for m in merged_msgs]
    assert positions == [1, 2, 3]

    merged_ids = [m.id for m in merged_msgs]
    assert id_a1 not in merged_ids
    assert id_a2 not in merged_ids
    assert id_b1 not in merged_ids

    assert count_messages_for_scene(session, scene_a.id) == 2
    assert count_messages_for_scene(session, scene_b.id) == 1

    session.close()
