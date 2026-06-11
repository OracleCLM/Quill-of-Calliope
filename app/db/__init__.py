import os
import sqlite3
import uuid
from pathlib import Path

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"
CALLIOPE_DB_PATH = Path(__file__).parent.parent.parent / "data" / "calliope.db"


def get_db(path: str | Path | None = None) -> sqlite3.Connection:
    if path is None:
        path = os.environ.get("CALLIOPE_DB_PATH") or CALLIOPE_DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_schema(conn: sqlite3.Connection, migrations_dir: Path = _MIGRATIONS_DIR) -> None:
    migration_files = sorted(migrations_dir.glob("*.sql"))
    for mf in migration_files:
        conn.executescript(mf.read_text(encoding="utf-8"))
    conn.commit()


def new_id() -> str:
    return str(uuid.uuid4())
