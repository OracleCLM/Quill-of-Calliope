import json

from app.calliope_shell.lore_kb import LoreEntry, LoreStore
from app.calliope_shell.scene_refine import refine_message
from app.db.characters import add_character_to_scene
from app.db.messages import add_message, get_message_by_id
from tests.unit.conftest import add_character, add_scene


def test_refine_message(db_connection, tmp_path):
    conn = db_connection["conn"]
    sid = add_scene(conn, "S1")
    cid = add_character(conn, "Aria")
    conn.execute(
        "UPDATE characters SET card_json=? WHERE id=?",
        (json.dumps({"traits": ["brave"]}), cid),
    )
    conn.commit()
    add_character_to_scene(conn, sid, cid, role="protagonist")
    mid = add_message(
        conn,
        scene_id=sid,
        character_id=cid,
        author_name="Aria",
        content_original="The drago appears.",
    )
    store = LoreStore(str(tmp_path / "lore.json"))
    store.add_entry(
        LoreEntry(
            id="e-drago", title="Drago", keys=["drago"], content="Antico custode."
        )
    )
    captured = {}

    def fake_ask(prompt):
        captured["prompt"] = prompt
        return "Enhanced prose."

    result = refine_message(mid, sid, conn, store, ask=fake_ask)

    assert result == "Enhanced prose."
    assert (
        get_message_by_id(conn, mid)["content_enhanced"] == "Enhanced prose."
    )
    assert "Aria" in captured["prompt"]
    assert "Drago" in captured["prompt"]
    assert "The drago appears." in captured["prompt"]
