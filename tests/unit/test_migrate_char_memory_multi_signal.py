"""
Unit test per scripts/migrate_char_memory_multi_signal.py.
migrate(db_path) è idempotente: aggiunge entities, char_facts FTS5, char_facts_meta.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.migrate_char_memory_multi_signal import migrate


def _make_base_db(path: Path) -> None:
    with sqlite3.connect(str(path)) as c:
        c.execute("CREATE TABLE char_state (id TEXT PRIMARY KEY, name TEXT)")
        c.commit()


def _columns(path: Path, table: str) -> set[str]:
    with sqlite3.connect(str(path)) as c:
        return {row[1] for row in c.execute(f"PRAGMA table_info({table})")}


def _tables(path: Path) -> set[str]:
    with sqlite3.connect(str(path)) as c:
        return {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}


# ── migrate ───────────────────────────────────────────────────────────────────

def test_migrate_adds_entities_column(tmp_path):
    db = tmp_path / "char_memory.db"
    _make_base_db(db)
    assert "entities" not in _columns(db, "char_state")
    migrate(db)
    assert "entities" in _columns(db, "char_state")


def test_migrate_creates_char_facts_fts(tmp_path):
    db = tmp_path / "char_memory.db"
    _make_base_db(db)
    migrate(db)
    assert "char_facts" in _tables(db)


def test_migrate_creates_char_facts_meta(tmp_path):
    db = tmp_path / "char_memory.db"
    _make_base_db(db)
    migrate(db)
    assert "char_facts_meta" in _tables(db)


def test_migrate_idempotent(tmp_path):
    db = tmp_path / "char_memory.db"
    _make_base_db(db)
    migrate(db)
    migrate(db)  # seconda esecuzione non deve sollevare eccezioni
    assert "entities" in _columns(db, "char_state")
    assert "char_facts" in _tables(db)
    assert "char_facts_meta" in _tables(db)


def test_migrate_db_not_found_exits(tmp_path):
    missing = tmp_path / "missing.db"
    with pytest.raises(SystemExit):
        migrate(missing)


def test_migrate_char_facts_meta_columns(tmp_path):
    db = tmp_path / "char_memory.db"
    _make_base_db(db)
    migrate(db)
    cols = _columns(db, "char_facts_meta")
    assert {"fact_id", "char_name", "scope", "created_at"} <= cols
