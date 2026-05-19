"""SQLite-backed character state storage for Quill of Calliope shell."""
import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).parents[2] / "data" / "char_memory.db"
_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    try:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _lock, _conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS char_state (
                    name TEXT PRIMARY KEY,
                    traits TEXT,
                    last_action TEXT,
                    relationships TEXT,
                    last_scene_id TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    except Exception as exc:
        logger.warning("char_memory init_db failed: %s", exc)


def get_char(name: str) -> Optional[dict]:
    try:
        with _lock, _conn() as c:
            row = c.execute(
                "SELECT * FROM char_state WHERE name = ?", (name,)
            ).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["traits"] = json.loads(d["traits"] or "{}")
        d["relationships"] = json.loads(d["relationships"] or "{}")
        return d
    except Exception as exc:
        logger.warning("char_memory get_char failed: %s", exc)
        return None


def upsert_char(
    name: str,
    traits: Optional[dict] = None,
    last_action: Optional[str] = None,
    relationships: Optional[dict] = None,
    last_scene_id: Optional[str] = None,
) -> None:
    try:
        existing = get_char(name) or {}
        new_traits = traits if traits is not None else existing.get("traits", {})
        new_rels = relationships if relationships is not None else existing.get("relationships", {})
        new_action = last_action if last_action is not None else existing.get("last_action")
        new_scene = last_scene_id if last_scene_id is not None else existing.get("last_scene_id")
        with _lock, _conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO char_state
                   (name, traits, last_action, relationships, last_scene_id, updated_at)
                   VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (
                    name,
                    json.dumps(new_traits),
                    new_action,
                    json.dumps(new_rels),
                    new_scene,
                ),
            )
    except Exception as exc:
        logger.warning("char_memory upsert_char failed: %s", exc)


def list_chars() -> list:
    try:
        with _lock, _conn() as c:
            rows = c.execute(
                "SELECT name, traits, updated_at FROM char_state ORDER BY updated_at DESC"
            ).fetchall()
        result = []
        for row in rows:
            traits_data = json.loads(row["traits"] or "{}")
            personality = traits_data.get("personality", [])
            summary = ", ".join(personality[:3]) if personality else ""
            result.append({
                "name": row["name"],
                "traits_summary": summary,
                "updated_at": row["updated_at"],
            })
        return result
    except Exception as exc:
        logger.warning("char_memory list_chars failed: %s", exc)
        return []


def delete_char(name: str) -> bool:
    try:
        with _lock, _conn() as c:
            cur = c.execute("DELETE FROM char_state WHERE name = ?", (name,))
        return cur.rowcount > 0
    except Exception as exc:
        logger.warning("char_memory delete_char failed: %s", exc)
        return False


init_db()
