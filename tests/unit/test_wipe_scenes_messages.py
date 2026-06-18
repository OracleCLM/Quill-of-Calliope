"""
Test per scripts/wipe_scenes_messages.py.

Garanzie verificate:
  - DRY-RUN (default) NON modifica il DB: conteggio righe invariato prima/dopo
    e ritorna conteggi coerenti con i dati inseriti.
  - --confirm-wipe svuota scenes+messages e crea un backup PRE-wipe.
  - Idempotenza: doppio dry-run e doppio wipe non sollevano errori.

Usa un DB temporaneo costruito con lo schema reale (app.db.init_schema), MAI il
DB di produzione.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from app.db import get_db, init_schema, new_id

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "wipe_scenes_messages.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("wipe_scenes_messages", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def seeded_db(tmp_path):
    db_path = tmp_path / "calliope_test.db"
    conn = get_db(str(db_path))
    init_schema(conn)
    # 2 scene, 3 messaggi.
    s1, s2 = new_id(), new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (s1, "Scene A"))
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (s2, "Scene B"))
    for i, sid in enumerate([s1, s1, s2]):
        conn.execute(
            "INSERT INTO messages (id, scene_id, author_name, content_original, ts, position_order) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (new_id(), sid, "Mao", f"msg {i}", "2026-06-18T00:00:00Z", i),
        )
    conn.commit()
    conn.close()
    return db_path


def test_dry_run_does_not_mutate(seeded_db, capsys):
    mod = _load_module()
    before = mod.count_rows(seeded_db)
    assert before == {"scenes": 2, "messages": 3}

    rc = mod.main(["--db", str(seeded_db)])
    assert rc == 0

    after = mod.count_rows(seeded_db)
    assert after == before, "dry-run NON deve modificare il DB"

    out = capsys.readouterr().out
    assert "scenes=2 messages=3" in out
    assert "dry-run" in out.lower()


def test_dry_run_idempotent(seeded_db):
    mod = _load_module()
    assert mod.main(["--db", str(seeded_db)]) == 0
    assert mod.main(["--db", str(seeded_db)]) == 0
    assert mod.count_rows(seeded_db) == {"scenes": 2, "messages": 3}


def test_confirm_wipe_clears_and_backs_up(seeded_db, tmp_path, monkeypatch):
    mod = _load_module()
    # Reindirizza backup in tmp per non toccare data/backups reale.
    backups = tmp_path / "backups"
    monkeypatch.setattr(mod, "BACKUPS_DIR", backups)
    scenes_dir = tmp_path / "scenes"
    scenes_dir.mkdir()
    (scenes_dir / "scene_001.yaml").write_text("title: x")

    rc = mod.main([
        "--db", str(seeded_db),
        "--scenes-dir", str(scenes_dir),
        "--runid", "TESTRUN",
        "--confirm-wipe",
    ])
    assert rc == 0
    assert mod.count_rows(seeded_db) == {"scenes": 0, "messages": 0}

    backup_dir = backups / "wipe_TESTRUN"
    assert (backup_dir / seeded_db.name).exists(), "backup DB mancante"
    assert (backup_dir / "scenes.tar.gz").exists(), "backup scenes mancante"


def test_wipe_idempotent(seeded_db, tmp_path, monkeypatch):
    mod = _load_module()
    monkeypatch.setattr(mod, "BACKUPS_DIR", tmp_path / "backups")
    args = ["--db", str(seeded_db), "--runid", "R", "--confirm-wipe",
            "--scenes-dir", str(tmp_path / "noexist")]
    assert mod.main(args) == 0
    assert mod.main(args) == 0  # secondo run su DB già vuoto = no-op
    assert mod.count_rows(seeded_db) == {"scenes": 0, "messages": 0}


def test_count_missing_db(tmp_path):
    mod = _load_module()
    assert mod.count_rows(tmp_path / "nope.db") == {"scenes": 0, "messages": 0}
