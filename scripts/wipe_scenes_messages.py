#!/usr/bin/env python3
"""
Wipe TUTTE le scene + tutti i messaggi dallo store Calliope.

STORE REALE (scoperto 2026-06-18, sprint R-CALLIOPE-CLEANUP-WIPE-PREP):
  - DB SQLite: data/calliope.db (override via env CALLIOPE_DB_PATH).
    Tabelle: `scenes`, `messages` (+ `scene_characters`, `scene_reactions` con
    ON DELETE CASCADE su scenes). Vedi app/db/migrations/*.sql.
  - Dir legacy: scenes/ (YAML draft) — NON è lo store live ma viene comunque
    inclusa nel backup per sicurezza.

SICUREZZA — GATED BY DEFAULT:
  - Senza flag -> DRY-RUN: conta soltanto, NON tocca nulla, exit 0.
  - `--confirm-wipe` -> esegue il delete reale. PRIMA crea un backup completo
    (copia DB + tar di scenes/) in data/backups/wipe_<runid>/.

Idempotente: ri-eseguibile senza errori (delete su tabelle vuote = no-op).

USO:
    python scripts/wipe_scenes_messages.py                 # dry-run (default)
    python scripts/wipe_scenes_messages.py --confirm-wipe  # wipe reale + backup
    python scripts/wipe_scenes_messages.py --confirm-wipe --runid 20260618_120000
    python scripts/wipe_scenes_messages.py --db /tmp/test.db   # store custom
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
import tarfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO_ROOT / "data" / "calliope.db"
DEFAULT_SCENES_DIR = REPO_ROOT / "scenes"
BACKUPS_DIR = REPO_ROOT / "data" / "backups"

# Tabelle da svuotare. `scenes` ha ON DELETE CASCADE su messages/scene_characters/
# scene_reactions, ma le elenchiamo esplicitamente per robustezza (idempotenza
# anche se le FK pragma non fossero attive) e per un logging chiaro.
WIPE_TABLES = ("messages", "scene_reactions", "scene_characters", "scenes")
COUNT_TABLES = ("scenes", "messages")


def _resolve_db(db_arg: str | None) -> Path:
    if db_arg:
        return Path(db_arg)
    env = os.environ.get("CALLIOPE_DB_PATH")
    if env:
        return Path(env)
    return DEFAULT_DB


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def count_rows(db_path: Path) -> dict[str, int]:
    """Conta scene + messaggi. DB assente o tabella assente -> 0 (idempotente)."""
    counts = {t: 0 for t in COUNT_TABLES}
    if not db_path.exists():
        return counts
    conn = sqlite3.connect(str(db_path))
    try:
        for t in COUNT_TABLES:
            if _table_exists(conn, t):
                counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    finally:
        conn.close()
    return counts


def _make_runid(arg: str | None) -> str:
    if arg:
        return arg
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def make_backup(db_path: Path, scenes_dir: Path, runid: str) -> Path:
    """Backup PRE-wipe: copia file DB (+ -wal/-shm) e tar di scenes/."""
    dest = BACKUPS_DIR / f"wipe_{runid}"
    dest.mkdir(parents=True, exist_ok=True)

    if db_path.exists():
        shutil.copy2(db_path, dest / db_path.name)
        print(f"[backup] DB -> {dest / db_path.name}")
        # WAL/SHM sidecar se presenti (dati non ancora checkpointati).
        for suffix in ("-wal", "-shm"):
            side = Path(str(db_path) + suffix)
            if side.exists():
                shutil.copy2(side, dest / side.name)
                print(f"[backup] {side.name} -> {dest / side.name}")
    else:
        print(f"[backup] DB assente ({db_path}) — niente da copiare")

    if scenes_dir.exists() and scenes_dir.is_dir():
        tar_path = dest / "scenes.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(scenes_dir, arcname=scenes_dir.name)
        print(f"[backup] scenes/ -> {tar_path}")
    else:
        print(f"[backup] dir scenes assente ({scenes_dir}) — skip tar")

    print(f"[backup] completato in {dest}")
    return dest


def wipe(db_path: Path) -> dict[str, int]:
    """Elimina scene + messaggi (+ tabelle dipendenti). Idempotente."""
    deleted = {t: 0 for t in WIPE_TABLES}
    if not db_path.exists():
        print(f"[wipe] DB assente ({db_path}) — niente da eliminare")
        return deleted
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        for t in WIPE_TABLES:
            if _table_exists(conn, t):
                cur = conn.execute(f"DELETE FROM {t}")
                deleted[t] = cur.rowcount if cur.rowcount is not None else 0
                print(f"[wipe] {t}: eliminate {deleted[t]} righe")
        conn.commit()
    finally:
        conn.close()
    return deleted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Wipe scene + messaggi Calliope (dry-run di default)."
    )
    parser.add_argument(
        "--confirm-wipe", action="store_true",
        help="Esegue il delete reale (con backup PRE-wipe). Senza, è solo dry-run.",
    )
    parser.add_argument("--db", default=None, help="Path DB override (default: data/calliope.db o env CALLIOPE_DB_PATH).")
    parser.add_argument("--scenes-dir", default=None, help="Path dir scenes/ da includere nel backup.")
    parser.add_argument("--runid", default=None, help="Runid backup (default: timestamp).")
    args = parser.parse_args(argv)

    db_path = _resolve_db(args.db)
    scenes_dir = Path(args.scenes_dir) if args.scenes_dir else DEFAULT_SCENES_DIR

    print(f"[info] DB store: {db_path}")
    print(f"[info] scenes dir: {scenes_dir}")

    before = count_rows(db_path)
    print(f"[count] scenes={before['scenes']} messages={before['messages']}")

    if not args.confirm_wipe:
        print("[dry-run] Nessuna modifica eseguita. "
              "Usa --confirm-wipe per eliminare davvero.")
        return 0

    runid = _make_runid(args.runid)
    print(f"[wipe] CONFERMATO — runid={runid}")
    make_backup(db_path, scenes_dir, runid)
    deleted = wipe(db_path)

    after = count_rows(db_path)
    print(f"[count] post-wipe scenes={after['scenes']} messages={after['messages']}")
    print("[done] eliminate: "
          + ", ".join(f"{t}={deleted[t]}" for t in WIPE_TABLES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
