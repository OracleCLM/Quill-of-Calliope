from app.db.messages import add_message, get_message_by_id
from tests.unit.conftest import add_character, add_scene
def test_add_message(msg_conn):
    """add_message inserisce un messaggio e restituisce l'ID."""
    scene_id = add_scene(msg_conn, "test_scene")
    char_id = add_character(msg_conn, "test_char")

    message_id = add_message(
        msg_conn,
        scene_id=scene_id,
        character_id=char_id,
        content_original="test message",
        content_rendered="<p>test message</p>",
        position_order=1,
    )

    assert message_id is not None
    assert isinstance(message_id, str)

    # Verifica che il messaggio sia stato inserito
    msg = get_message_by_id(msg_conn, message_id)
    assert msg is not None
    assert msg["content_original"] == "test message"
    assert msg["scene_id"] == scene_id
    assert msg["character_id"] == char_id
