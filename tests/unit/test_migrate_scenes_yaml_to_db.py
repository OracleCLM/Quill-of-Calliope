"""
Unit test per scripts/migrate_scenes_yaml_to_db.py (VG-2).

Contratto:
  - Scene con titolo assente → skip
  - Scene già presente nel DB (per titolo) → skip (idempotenza)
  - Scene nuova → inserita con title, last_activity_at, created_at
  - first_msg_excerpt / last_msg_excerpt → messaggi is_summary=1
  - Excerpt vuoti → nessun messaggio inserito
  - --dry-run → nessuna scrittura nel DB
  - YAML senza scene YAML valide → 0 importate (nessun crash)
"""
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.migrate_scenes_yaml_to_db import _migrate_scene, main


# ── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE scenes (
            id TEXT PRIMARY KEY,
            title TEXT,
            arc_id TEXT,
            is_readonly INTEGER DEFAULT 0,
            last_activity_at TEXT,
            created_at TEXT,
            location TEXT,
            updated_at TEXT
        );
        CREATE TABLE messages (
            id TEXT PRIMARY KEY,
            scene_id TEXT NOT NULL,
            author_name TEXT,
            content_original TEXT,
            ts TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'manual',
            position_order INTEGER NOT NULL DEFAULT 0,
            is_summary INTEGER DEFAULT 0,
            character_id TEXT,
            content_enhanced TEXT
        );
    """)
    conn.commit()
    yield conn, db_path
    conn.close()
    Path(db_path).unlink(missing_ok=True)


_SCENE_DATA = {
    "scene_id": "scene_99",
    "title": "Scene 99: Aurora e Katsuro",
    "date_started": "2022-01-01",
    "last_active": "2022-01-02",
    "participants": ["Aurora", "Katsuro"],
    "first_msg_excerpt": "Aurora si avvicinò al tavolo.",
    "last_msg_excerpt": "Katsuro annuì in silenzio.",
    "summary": None,
}


# ── Test _migrate_scene ───────────────────────────────────────────────────────

def test_scene_inserted(tmp_db):
    conn, _ = tmp_db
    ok, reason = _migrate_scene(conn, _SCENE_DATA, dry_run=False)
    assert ok
    row = conn.execute("SELECT title FROM scenes WHERE title = ?", (_SCENE_DATA["title"],)).fetchone()
    assert row is not None


def test_idempotent_skip(tmp_db):
    conn, _ = tmp_db
    _migrate_scene(conn, _SCENE_DATA, dry_run=False)
    ok, reason = _migrate_scene(conn, _SCENE_DATA, dry_run=False)
    assert not ok
    assert "presente" in reason
    count = conn.execute("SELECT COUNT(*) FROM scenes WHERE title = ?", (_SCENE_DATA["title"],)).fetchone()[0]
    assert count == 1


def test_missing_title_skip(tmp_db):
    conn, _ = tmp_db
    data = {**_SCENE_DATA, "title": ""}
    ok, reason = _migrate_scene(conn, data, dry_run=False)
    assert not ok
    assert "title" in reason


def test_excerpts_inserted_as_summary_messages(tmp_db):
    conn, _ = tmp_db
    _migrate_scene(conn, _SCENE_DATA, dry_run=False)
    msgs = conn.execute("SELECT is_summary, content_original FROM messages ORDER BY position_order").fetchall()
    assert len(msgs) == 2
    assert all(m[0] == 1 for m in msgs)
    contents = [m[1] for m in msgs]
    assert "Aurora si avvicinò" in contents[0]
    assert "Katsuro annuì" in contents[1]


def test_empty_excerpts_no_messages(tmp_db):
    conn, _ = tmp_db
    data = {**_SCENE_DATA, "title": "Scene 200: Vuota", "first_msg_excerpt": "", "last_msg_excerpt": None}
    _migrate_scene(conn, data, dry_run=False)
    count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    assert count == 0


def test_dry_run_no_write(tmp_db):
    conn, _ = tmp_db
    ok, _ = _migrate_scene(conn, _SCENE_DATA, dry_run=True)
    assert ok
    count = conn.execute("SELECT COUNT(*) FROM scenes").fetchone()[0]
    assert count == 0


def test_last_activity_set(tmp_db):
    conn, _ = tmp_db
    _migrate_scene(conn, _SCENE_DATA, dry_run=False)
    row = conn.execute("SELECT last_activity_at FROM scenes WHERE title = ?", (_SCENE_DATA["title"],)).fetchone()
    assert row[0] == "2022-01-02"


def test_created_at_set(tmp_db):
    conn, _ = tmp_db
    _migrate_scene(conn, _SCENE_DATA, dry_run=False)
    row = conn.execute("SELECT created_at FROM scenes WHERE title = ?", (_SCENE_DATA["title"],)).fetchone()
    assert row[0] == "2022-01-01"


# ── Test main() CLI ───────────────────────────────────────────────────────────

def test_main_imports_yaml(tmp_db, tmp_path):
    conn, db_path = tmp_db
    yaml_file = tmp_path / "scene_99.yaml"
    yaml_file.write_text(yaml.dump(_SCENE_DATA), encoding="utf-8")
    main(["--scenes-dir", str(tmp_path), "--db-path", db_path])
    count = conn.execute("SELECT COUNT(*) FROM scenes").fetchone()[0]
    assert count == 1


def test_main_dry_run_no_write(tmp_db, tmp_path):
    conn, db_path = tmp_db
    yaml_file = tmp_path / "scene_dry.yaml"
    yaml_file.write_text(yaml.dump(_SCENE_DATA), encoding="utf-8")
    main(["--scenes-dir", str(tmp_path), "--db-path", db_path, "--dry-run"])
    count = conn.execute("SELECT COUNT(*) FROM scenes").fetchone()[0]
    assert count == 0


def test_main_empty_dir(tmp_db, tmp_path, capsys):
    _, db_path = tmp_db
    main(["--scenes-dir", str(tmp_path), "--db-path", db_path])
    out = capsys.readouterr().out
    assert "Nessun" in out or "0" in out


# ── coverage gaps (lines 78-79, 99-103) ──────────────────────────────────────

def test_main_nonexistent_dir_exits_1(tmp_db, capsys):
    """scenes-dir non trovata → lines 78-79: print stderr + sys.exit(1)."""
    _, db_path = tmp_db
    with pytest.raises(SystemExit) as exc_info:
        main(["--scenes-dir", "/tmp/no_such_dir_calliope_test", "--db-path", db_path])
    assert exc_info.value.code == 1
    assert "ERRORE" in capsys.readouterr().err


def test_main_skip_branch_covered(tmp_db, tmp_path, capsys):
    """_migrate_scene torna (False, reason) → lines 99-100: SKIP printed."""
    _, db_path = tmp_db
    scene_file = tmp_path / "no_title.yaml"
    scene_file.write_text(yaml.dump({"participants": ["Alice"]}), encoding="utf-8")
    main(["--scenes-dir", str(tmp_path), "--db-path", db_path])
    out = capsys.readouterr().out
    assert "SKIP" in out


def test_main_exception_branch_covered(tmp_db, tmp_path, capsys):
    """yaml.safe_load lancia eccezione → lines 102-103: ERRORE su stderr."""
    from unittest.mock import patch
    _, db_path = tmp_db
    scene_file = tmp_path / "bad.yaml"
    scene_file.write_text(yaml.dump({"title": "Test"}), encoding="utf-8")
    with patch("scripts.migrate_scenes_yaml_to_db.yaml.safe_load", side_effect=ValueError("yaml broken")):
        main(["--scenes-dir", str(tmp_path), "--db-path", db_path])
    err = capsys.readouterr().err
    assert "ERRORE" in err
