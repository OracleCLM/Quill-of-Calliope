#!/usr/bin/env python3
"""Idempotent migration: extend char_memory.db for multi-signal retrieval.

Adds:
- entities column to char_state (if missing)
- char_facts FTS5 virtual table (if missing)
- char_facts_meta auxiliary table (if missing)

Safe to run multiple times. Non-destructive.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

DB_PATH = Path(__file__).parents[1] / "data" / "char_memory.db"


def migrate(db_path: Path = DB_PATH) -> None:
    if not db_path.exists():
        print(f"DB not found at {db_path} — run seed_char_memory.py first")
        sys.exit(1)

    with sqlite3.connect(str(db_path)) as c:
        # 1. Add entities column to char_state
        existing = {row[1] for row in c.execute("PRAGMA table_info(char_state)")}
        if "entities" not in existing:
            c.execute("ALTER TABLE char_state ADD COLUMN entities TEXT DEFAULT '[]'")
            print("  ✓ Added entities column to char_state")
        else:
            print("  · entities column already present")

        # 2. FTS5 char_facts
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "char_facts" not in tables:
            c.execute("""
                CREATE VIRTUAL TABLE char_facts USING fts5(
                    fact_id UNINDEXED,
                    char_name,
                    fact_text,
                    entities UNINDEXED,
                    scope UNINDEXED,
                    created_at UNINDEXED,
                    tokenize='unicode61'
                )
            """)
            print("  ✓ Created char_facts FTS5 table")
        else:
            print("  · char_facts already present")

        # 3. char_facts_meta
        if "char_facts_meta" not in tables:
            c.execute("""
                CREATE TABLE char_facts_meta (
                    fact_id TEXT PRIMARY KEY,
                    char_name TEXT NOT NULL,
                    scope TEXT NOT NULL DEFAULT 'L1',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("  ✓ Created char_facts_meta table")
        else:
            print("  · char_facts_meta already present")

        c.commit()
    print(f"\nMigration complete → {db_path}")


if __name__ == "__main__":
    print(f"Migrating char_memory DB: {DB_PATH}")
    migrate()
