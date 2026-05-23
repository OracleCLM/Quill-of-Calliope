"""Audit trail for Calliope write events (Sprint C1).

Q5 operator-decision = livello (b): log only state-mutating events
(create/save/update/delete/export). NO read/browse events.

Schema lives in the shared data/char_memory.db so existing PRAGMA
journal_mode=WAL (Wave 8) applies. Single append-only table; the
activity-feed UI reads it via /api/dashboard/activity (Sprint C3).

Helper functions are intentionally small and synchronous — write events
must record before the action commits (the alternative, async write,
risks losing trail on crash).
"""
from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).parents[2] / "data" / "char_memory.db"
_lock = threading.Lock()

# Allowed event kinds — keep narrow. Adding a new kind requires
# explicit code change so we don't accumulate noisy categories.
EVENT_KINDS = frozenset({
    "char.create",
    "char.update",
    "char.fact_append",
    "char.fact_replace",
    "arc.create",
    "arc.scene_append",
    "arc.summary_regen",
    "scene.refine",
    "scene.variants_generated",
    "scene.blend",
    "scene.next_msg",
    "translate.run",
    "llm_routing.switch",
})

# "Highlight" subset = operator-perceived events (the ones the operator
# would call out when describing what happened today). Verbose mode shows
# everything; highlight shows only this subset.
HIGHLIGHT_KINDS = frozenset({
    "char.create",
    "arc.create",
    "scene.refine",
    "scene.blend",
    "scene.next_msg",
    "llm_routing.switch",
})


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    return c


def init_db() -> None:
    """Create audit_trail table if missing. Idempotent."""
    try:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _lock, _conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS audit_trail (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    kind TEXT NOT NULL,
                    subject TEXT,
                    detail TEXT,
                    metadata_json TEXT DEFAULT '{}'
                )
            """)
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_trail(ts DESC)"
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_kind_ts "
                "ON audit_trail(kind, ts DESC)"
            )
    except Exception as exc:
        logger.warning("audit_trail init_db failed: %s", exc)


def log_event(
    kind: str,
    subject: Optional[str] = None,
    detail: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    """Append a write event. Silently no-op on unknown kind or DB error
    (audit must never break the operation it observes)."""
    if kind not in EVENT_KINDS:
        logger.debug("audit_trail: rejected unknown kind %r", kind)
        return
    import json  # noqa: PLC0415
    try:
        meta_json = json.dumps(metadata or {}, ensure_ascii=False, default=str)
        with _lock, _conn() as c:
            c.execute(
                "INSERT INTO audit_trail (kind, subject, detail, metadata_json) "
                "VALUES (?, ?, ?, ?)",
                (kind, subject, detail, meta_json),
            )
    except Exception as exc:
        logger.warning("audit_trail.log_event failed: %s", exc)


def recent_events(
    limit: int = 20,
    mode: str = "highlight",
    kinds_filter: Optional[Iterable[str]] = None,
) -> list[dict]:
    """Read recent events. mode: 'verbose' = all kinds, 'highlight' = subset.

    On-demand mode is the API-level concept (UI calls only when user asks)
    so it's not a separate query mode here.
    """
    try:
        if kinds_filter is not None:
            kinds = tuple(kinds_filter)
        elif mode == "verbose":
            kinds = tuple(EVENT_KINDS)
        else:
            kinds = tuple(HIGHLIGHT_KINDS)
        if not kinds:
            return []
        placeholders = ",".join("?" * len(kinds))
        with _conn() as c:
            rows = c.execute(
                f"SELECT event_id, ts, kind, subject, detail, metadata_json "
                f"FROM audit_trail "
                f"WHERE kind IN ({placeholders}) "
                f"ORDER BY event_id DESC LIMIT ?",
                (*kinds, limit),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("audit_trail.recent_events failed: %s", exc)
        return []
