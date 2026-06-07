import pytest
from app.db.lore import add_lore_entry
def test_add_lore_entry_with_empty_title(db_connection):
    """add_lore_entry con titolo vuoto solleva ValueError."""
    conn = db_connection["conn"]
    with pytest.raises(ValueError):
        add_lore_entry(conn, title="", content_text="Some content")

def test_add_lore_entry_with_long_title(db_connection):
    """add_lore_entry con titolo >255 caratteri solleva ValueError."""
    conn = db_connection["conn"]
    long_title = "a" * 256
    with pytest.raises(ValueError):
        add_lore_entry(conn, title=long_title, content_text="Some content")
