"""VG-2 — Migra scene flat-YAML → DB scene-as-chat.

Idempotente: salta scene già presenti (match per titolo).
Inserisce:
  - record scenes (title, last_activity_at, created_at)
  - first_msg_excerpt + last_msg_excerpt come messaggi is_summary=1 (se presenti)

NON inserisce scene_characters: character_id NOT NULL richiede UUID validi.
Wiring roster = passo separato dopo migrate_chars_to_ssot.py.

Usage:
    python scripts/migrate_scenes_yaml_to_db.py [--scenes-dir scenes/] [--db-path data/calliope.db] [--dry-run]
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import uuid
from pathlib import Path

import yaml


def _new_id() -> str:
    return str(uuid.uuid4())


def _migrate_scene(conn: sqlite3.Connection, data: dict, dry_run: bool) -> tuple[bool, str]:
    """Migra una singola scena. Ritorna (migrated, reason)."""
    title = (data.get("title") or "").strip()
    if not title:
        return False, "title mancante"

    existing = conn.execute("SELECT 1 FROM scenes WHERE title = ?", (title,)).fetchone()
    if existing:
        return False, "già presente"

    scene_id = _new_id()
    last_active = data.get("last_active") or data.get("timestamp_end") or None
    created_at = data.get("date_started") or data.get("timestamp_start") or None

    if not dry_run:
        conn.execute(
            "INSERT INTO scenes (id, title, last_activity_at, created_at) VALUES (?, ?, ?, ?)",
            (scene_id, title, last_active, created_at),
        )

        # Inserisci first_msg_excerpt e last_msg_excerpt come messaggi riassuntivi
        excerpts = [
            ("SISTEMA", (data.get("first_msg_excerpt") or "").strip(), 0),
            ("SISTEMA", (data.get("last_msg_excerpt") or "").strip(), 1),
        ]
        for (author, content, order) in excerpts:
            if content:
                conn.execute(
                    """INSERT INTO messages
                       (id, scene_id, author_name, content_original, ts, source, position_order, is_summary)
                       VALUES (?, ?, ?, ?, datetime('now'), ?, ?, 1)""",
                    (_new_id(), scene_id, author, content, "yaml_import", order),
                )

        conn.commit()

    return True, "importata"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Migra scene flat-YAML → DB (VG-2)")
    parser.add_argument("--scenes-dir", default="scenes", help="directory YAML scene")
    parser.add_argument("--db-path", default="data/calliope.db", help="path SQLite DB")
    parser.add_argument("--dry-run", action="store_true", help="simula senza scrivere")
    args = parser.parse_args(argv)

    scenes_dir = Path(args.scenes_dir)
    if not scenes_dir.is_dir():
        print(f"[ERRORE] scenes-dir non trovata: {scenes_dir}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(args.db_path)
    conn.execute("PRAGMA foreign_keys=OFF")  # participants senza char UUID

    yaml_files = sorted(scenes_dir.glob("*.yaml"))
    if not yaml_files:
        print("[INFO] Nessun file YAML trovato in", scenes_dir)
        return

    imported = skipped = errors = 0
    for yf in yaml_files:
        try:
            data = yaml.safe_load(yf.read_text(encoding="utf-8")) or {}
            ok, reason = _migrate_scene(conn, data, dry_run=args.dry_run)
            if ok:
                imported += 1
                prefix = "[DRY-RUN]" if args.dry_run else "[OK]"
                print(f"{prefix} {yf.name}: {data.get('title', '?')}")
            else:
                skipped += 1
                print(f"[SKIP] {yf.name}: {reason}")
        except Exception as exc:
            errors += 1
            print(f"[ERRORE] {yf.name}: {exc}", file=sys.stderr)

    conn.close()
    mode = " (dry-run)" if args.dry_run else ""
    print(f"\nRisultato{mode}: {imported} importate, {skipped} saltate, {errors} errori")


if __name__ == "__main__":
    main()
