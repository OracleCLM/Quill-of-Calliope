import json

from app.calliope_shell.scene_retrieval import retrieve_scene_sheets
from app.db.characters import add_character_to_scene
from tests.unit.conftest import add_character, add_scene


def test_retrieve_scene_sheets(db_connection):
    conn = db_connection["conn"]
    sid = add_scene(conn, "S1")
    cid = add_character(conn, "Aria")

    card_data = {
        "traits": ["brave"],
        "backstory": "x" * 400,
        "speech_pattern": {"tone": "calm"},
    }
    conn.execute(
        "UPDATE characters SET card_json=? WHERE id=?",
        (json.dumps(card_data), cid),
    )
    conn.commit()

    add_character_to_scene(conn, sid, cid, role="protagonist")
    sheets = retrieve_scene_sheets(sid, conn)

    assert len(sheets) == 1
    assert sheets[0]["character_id"] == cid
    assert sheets[0]["name"] == "Aria"
    assert sheets[0]["role"] == "protagonist"
    assert sheets[0]["traits"] == ["brave"]
    assert len(sheets[0]["backstory"]) == 300
    assert sheets[0]["speech_pattern"] == {"tone": "calm"}
