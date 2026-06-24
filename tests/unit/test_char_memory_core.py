"""Unit test per le funzioni SQLite core di app/calliope_shell/char_memory.py."""
import pytest
from unittest.mock import patch

from app.calliope_shell import char_memory


@pytest.fixture
def db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_char_mem.db"
    monkeypatch.setattr(char_memory, "_DB_PATH", db_path)
    char_memory.init_db()
    yield


def test_get_char_not_found(db):
    assert char_memory.get_char("Ghost") is None


def test_upsert_and_get_char(db):
    char_memory.upsert_char("Alice", traits={"color": "blue"})
    result = char_memory.get_char("Alice")
    assert result is not None
    assert "name" in result
    assert "traits" in result
    assert "relationships" in result
    assert "entities" in result


def test_upsert_is_idempotent(db):
    char_memory.upsert_char("Bob")
    char_memory.upsert_char("Bob")
    chars = char_memory.list_chars()
    assert len(chars) == 1


def test_upsert_partial_update_preserves_fields(db):
    char_memory.upsert_char("Charlie", traits={"x": 1})
    char_memory.upsert_char("Charlie", last_action="jumped")
    result = char_memory.get_char("Charlie")
    assert result["traits"] == {"x": 1}
    assert result["last_action"] == "jumped"


def test_list_chars_empty(db):
    assert char_memory.list_chars() == []


def test_list_chars_returns_all(db):
    char_memory.upsert_char("A")
    char_memory.upsert_char("B")
    chars = char_memory.list_chars()
    assert len(chars) == 2


def test_list_chars_contains_name(db):
    char_memory.upsert_char("Dave")
    chars = char_memory.list_chars()
    names = [c["name"] for c in chars]
    assert "Dave" in names


def test_delete_char_returns_true(db):
    char_memory.upsert_char("Eve")
    assert char_memory.delete_char("Eve") is True


def test_delete_char_not_found_returns_false(db):
    assert char_memory.delete_char("Nobody") is False


def test_delete_char_removes_from_list(db):
    char_memory.upsert_char("Frank")
    char_memory.delete_char("Frank")
    assert char_memory.list_chars() == []


def test_append_fact_returns_id(db):
    with patch("app.calliope_shell.entity_linker.extract_entities_for_fact", return_value=[]):
        char_memory.upsert_char("Grace")
        fact_id = char_memory.append_fact("Grace", "Grace runs")
    assert isinstance(fact_id, str)


def test_append_fact_l0_blocked(db):
    fact_id = char_memory.append_fact("Heidi", "x", scope="L0")
    assert fact_id is None


def test_append_fact_invalid_scope(db):
    fact_id = char_memory.append_fact("Ivan", "x", scope="INVALID")
    assert fact_id is None


def test_get_facts_empty(db):
    assert char_memory.get_facts("Judy") == []


def test_get_facts_returns_appended(db):
    with patch("app.calliope_shell.entity_linker.extract_entities_for_fact", return_value=[]):
        char_memory.upsert_char("Kevin")
        char_memory.append_fact("Kevin", "Kevin sleeps")
        facts = char_memory.get_facts("Kevin")
    assert len(facts) >= 1


def test_get_facts_contains_text(db):
    with patch("app.calliope_shell.entity_linker.extract_entities_for_fact", return_value=[]):
        char_memory.upsert_char("Leo")
        char_memory.append_fact("Leo", "Leo roars")
        facts = char_memory.get_facts("Leo")
    assert "Leo roars" in facts[0]["fact_text"]


def test_init_db_idempotent(db):
    char_memory.init_db()
    char_memory.init_db()


def test_upsert_traits_stored(db):
    char_memory.upsert_char("Mallory", traits={"personality": ["brave"]})
    result = char_memory.get_char("Mallory")
    assert result["traits"]["personality"] == ["brave"]
