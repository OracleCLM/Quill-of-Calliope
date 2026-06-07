import pytest
from app.db.characters import add_character
def test_add_character_with_empty_name(db_connection):
    """add_character con nome vuoto solleva ValueError."""
    conn = db_connection["conn"]
    with pytest.raises(ValueError):
        add_character(conn, name="")

def test_add_character_with_long_name(db_connection):
    """add_character con nome >255 caratteri solleva ValueError."""
    conn = db_connection["conn"]
    long_name = "a" * 256
    with pytest.raises(ValueError):
        add_character(conn, name=long_name)
