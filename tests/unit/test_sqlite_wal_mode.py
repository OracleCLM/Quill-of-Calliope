"""Regression test for P1 #11 — SQLite WAL mode enabled.

WAL (Write-Ahead Logging) lets readers proceed without blocking writers,
reducing lock contention seen in audit P1 #11. Verified by querying
PRAGMA journal_mode on a fresh connection.
"""
from __future__ import annotations

from app.calliope_shell.char_memory import _conn as char_conn
from app.calliope_shell.plot_arc import _conn as arc_conn, init_db as init_arc_db


def test_char_memory_uses_wal_mode():
    init_arc_db()  # ensure DB file exists
    with char_conn() as c:
        mode = c.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal", f"expected WAL, got {mode!r}"


def test_char_memory_synchronous_normal():
    with char_conn() as c:
        sync = c.execute("PRAGMA synchronous").fetchone()[0]
        # 1 = NORMAL (0=OFF, 1=NORMAL, 2=FULL, 3=EXTRA)
        assert sync == 1, f"expected synchronous=NORMAL (1), got {sync}"


def test_plot_arc_uses_wal_mode():
    init_arc_db()
    with arc_conn() as c:
        mode = c.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal", f"expected WAL, got {mode!r}"


def test_plot_arc_synchronous_normal():
    with arc_conn() as c:
        sync = c.execute("PRAGMA synchronous").fetchone()[0]
        assert sync == 1, f"expected synchronous=NORMAL (1), got {sync}"


def test_foreign_keys_still_enabled_plot_arc():
    """Regression: WAL change must not disable foreign_keys PRAGMA."""
    with arc_conn() as c:
        fk = c.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1
