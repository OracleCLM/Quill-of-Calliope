from tests.unit.test_reactions import _make_db
from app.db.reactions import add_reaction, list_reactions
def test_add_reaction_with_empty_emoji():
    """add_reaction con emoji vuota inserisce correttamente."""
    conn, db_path, char_id, msg_id = _make_db()
    try:
        reaction_id = add_reaction(conn, message_id=msg_id, character_id=char_id, emoji="")

        assert isinstance(reaction_id, str)

        reactions = list_reactions(conn, message_id=msg_id)
        assert len(reactions) == 1
        r = reactions[0]
        assert r["id"] == reaction_id
        assert r["message_id"] == msg_id
        assert r["character_id"] == char_id
        assert r["emoji"] == ""
    finally:
        conn.close()
        db_path.unlink(missing_ok=True)
