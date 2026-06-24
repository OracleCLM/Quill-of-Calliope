"""Unit test per le funzioni SQLite core di app/calliope_shell/char_memory.py."""
import sqlite3 as _sqlite3

import pytest
from unittest.mock import patch

from app.calliope_shell import char_memory

_CM = "app.calliope_shell.char_memory"


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


# ── replace_fact ──────────────────────────────────────────────────────────────

def test_replace_fact_l0_blocked(db):
    result = char_memory.replace_fact("Nav", "old", "new", scope="L0")
    assert result["success"] is False
    assert "L0" in result["error"]


def test_replace_fact_invalid_scope(db):
    result = char_memory.replace_fact("Nav", "old", "new", scope="INVALID")
    assert result["success"] is False


def test_replace_fact_replaces_text(db):
    with patch("app.calliope_shell.entity_linker.extract_entities_for_fact", return_value=[]):
        char_memory.upsert_char("Nav")
        char_memory.append_fact("Nav", "Nav wears a red cloak", scope="L1")
    result = char_memory.replace_fact("Nav", "red cloak", "blue cloak", scope="L1")
    assert result["success"] is True
    assert result["replaced"] == 1
    facts = char_memory.get_facts("Nav")
    assert "blue cloak" in facts[0]["fact_text"]


def test_replace_fact_no_match_returns_zero(db):
    with patch("app.calliope_shell.entity_linker.extract_entities_for_fact", return_value=[]):
        char_memory.upsert_char("Nav")
        char_memory.append_fact("Nav", "Nav wears a red cloak", scope="L1")
    result = char_memory.replace_fact("Nav", "green hat", "blue hat", scope="L1")
    assert result["success"] is True
    assert result["replaced"] == 0


# ── coverage gaps: scope filter + exception branches ─────────────────────────


def test_get_facts_with_scope_filter(db):
    with patch("app.calliope_shell.entity_linker.extract_entities_for_fact", return_value=[]):
        char_memory.upsert_char("Sam")
        char_memory.append_fact("Sam", "Fact A", scope="L1")
        char_memory.append_fact("Sam", "Fact B", scope="L2")
    facts = char_memory.get_facts("Sam", scope="L1")
    assert len(facts) == 1
    assert facts[0]["fact_text"] == "Fact A"


def test_get_char_db_error_returns_none(db):
    with patch(f"{_CM}._conn", side_effect=_sqlite3.OperationalError("fake")):
        assert char_memory.get_char("X") is None


def test_list_chars_db_error_returns_empty(db):
    with patch(f"{_CM}._conn", side_effect=_sqlite3.OperationalError("fake")):
        assert char_memory.list_chars() == []


def test_delete_char_db_error_returns_false(db):
    with patch(f"{_CM}._conn", side_effect=_sqlite3.OperationalError("fake")):
        assert char_memory.delete_char("X") is False


def test_append_fact_db_error_returns_none(db):
    with patch(f"{_CM}._conn", side_effect=_sqlite3.OperationalError("fake")):
        assert char_memory.append_fact("X", "y", scope="L1") is None


def test_replace_fact_db_error_returns_error_dict(db):
    with patch(f"{_CM}._conn", side_effect=_sqlite3.OperationalError("fake")):
        result = char_memory.replace_fact("X", "old", "new", scope="L1")
        assert result["success"] is False
        assert "error" in result


def test_get_facts_db_error_returns_empty(db):
    with patch(f"{_CM}._conn", side_effect=_sqlite3.OperationalError("fake")):
        assert char_memory.get_facts("X") == []


def test_init_db_exception_doesnt_propagate(tmp_path, monkeypatch):
    db_path = tmp_path / "bad.db"
    monkeypatch.setattr(char_memory, "_DB_PATH", db_path)
    with patch(f"{_CM}._conn", side_effect=_sqlite3.OperationalError("disk full")):
        char_memory.init_db()


def test_upsert_char_db_error_doesnt_raise(db):
    with patch(f"{_CM}._conn", side_effect=_sqlite3.OperationalError("disk full")):
        char_memory.upsert_char("Victim", traits={"x": 1})


def test_retrieve_multi_signal_entity_overlap_runs(db):
    with patch("app.calliope_shell.entity_linker.extract_entities_for_fact", return_value=[]):
        char_memory.upsert_char("Hero")
        char_memory.append_fact("Hero", "Hero coordinated with NATO", scope="L1")
    result = char_memory.retrieve_multi_signal("Hero", "NATO alliance", top_k=3)
    assert isinstance(result, list)


def test_retrieve_multi_signal_bm25_exception_continues(db):
    call_count = [0]
    real_conn = char_memory._conn

    def maybe_fail():
        call_count[0] += 1
        if call_count[0] == 1:
            raise _sqlite3.OperationalError("BM25 fake fail")
        return real_conn()

    with patch(f"{_CM}._conn", side_effect=maybe_fail):
        result = char_memory.retrieve_multi_signal("X", "query")
    assert isinstance(result, list)


def test_retrieve_multi_signal_entity_hits_branch(db):
    char_memory.upsert_char("Heroine")
    char_memory.append_fact("Heroine", "Heroine deployed with NATO", scope="L1")
    result = char_memory.retrieve_multi_signal("Heroine", "NATO operation", top_k=3)
    assert isinstance(result, list)


def test_retrieve_multi_signal_entity_overlap_exception(db):
    call_count = [0]
    real_conn = char_memory._conn

    def fail_on_second():
        call_count[0] += 1
        if call_count[0] == 2:
            raise _sqlite3.OperationalError("entity overlap fake fail")
        return real_conn()

    with patch(f"{_CM}._conn", side_effect=fail_on_second):
        result = char_memory.retrieve_multi_signal("X", "NATO forces")
    assert isinstance(result, list)
