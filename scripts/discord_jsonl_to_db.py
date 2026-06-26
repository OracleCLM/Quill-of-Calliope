"""Bridge: datasets/discord_yokai/messages_clean.jsonl → SQLite DB (source='discord').

Crea una scena per ogni canale Discord distinto e inserisce i messaggi IC.
Idempotente: salta messaggi già presenti (dedup su ts+author_name+channel).

Usage:
    python scripts/discord_jsonl_to_db.py [--input datasets/discord_yokai/messages_clean.jsonl]
    python scripts/discord_jsonl_to_db.py --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path

# Aggiungi la radice del progetto al path per import `app.*`
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db import get_db  # noqa: E402

logger = logging.getLogger(__name__)

DISCORD_SCENE_PREFIX = "discord_channel__"


def _channel_scene_title(channel_name: str) -> str:
    return f"[Discord] #{channel_name}"


def _get_or_create_scene(conn, channel_id: str, channel_name: str, dry_run: bool) -> str:
    """Restituisce l'id della scena per il canale Discord, creandola se necessaria."""
    scene_id = f"{DISCORD_SCENE_PREFIX}{channel_id}"
    row = conn.execute("SELECT id FROM scenes WHERE id = ?", (scene_id,)).fetchone()
    if row:
        return scene_id
    title = _channel_scene_title(channel_name)
    if not dry_run:
        conn.execute(
            "INSERT INTO scenes (id, title, location, is_readonly, created_at, updated_at) "
            "VALUES (?, ?, ?, 1, strftime('%Y-%m-%dT%H:%M:%SZ','now'), strftime('%Y-%m-%dT%H:%M:%SZ','now'))",
            (scene_id, title, f"Discord #{channel_name}"),
        )
        conn.commit()
        logger.info("  Created scene %s → %s", scene_id, title)
    else:
        logger.info("  [DRY-RUN] Would create scene %s → %s", scene_id, title)
    return scene_id


def _dedup_key(rec: dict) -> str:
    """Hash deterministico per idempotenza: channel_id + ts + author_name."""
    raw = f"{rec.get('channel_id','')}__{rec.get('timestamp','')}__{rec.get('author_name','')}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _dedup_key_exists(conn, scene_id: str, dedup_key: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM messages WHERE scene_id = ? AND id LIKE ?",
        (scene_id, f"disc_{dedup_key}%"),
    ).fetchone()
    return row is not None


def run(input_path: Path, dry_run: bool, only_ic: bool, limit: int | None) -> dict:
    conn = get_db()
    stats = {"inserted": 0, "skipped_tag": 0, "skipped_dedup": 0, "errors": 0}

    # Carica mappa character name → id dal DB
    char_rows = conn.execute("SELECT id, name FROM characters").fetchall()
    charmap = {r[1].lower(): r[0] for r in char_rows}
    logger.info("Loaded %d characters from DB", len(charmap))

    # Leggi JSONL
    with input_path.open(encoding="utf-8") as fh:
        lines = fh.readlines()
    logger.info("Reading %d lines from %s", len(lines), input_path)

    if limit:
        lines = lines[:limit]

    # Raggruppa per (channel_id, channel_name)
    records_by_channel: dict[str, list[dict]] = {}
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("JSON parse error: %s", exc)
            stats["errors"] += 1
            continue
        tag = rec.get("tag", "")
        if only_ic and tag != "IC":
            stats["skipped_tag"] += 1
            continue
        cid = rec.get("channel_id", "unknown")
        records_by_channel.setdefault(cid, []).append(rec)

    logger.info("Channels to process: %d", len(records_by_channel))

    for channel_id, recs in records_by_channel.items():
        channel_name = recs[0].get("channel_name", channel_id)
        scene_id = _get_or_create_scene(conn, channel_id, channel_name, dry_run)

        # Ordina per timestamp
        recs.sort(key=lambda r: r.get("timestamp", ""))

        for pos, rec in enumerate(recs):
            dedup = _dedup_key(rec)
            if _dedup_key_exists(conn, scene_id, dedup):
                stats["skipped_dedup"] += 1
                continue

            author = rec.get("author_nick") or rec.get("author_name") or "unknown"
            content = rec.get("content") or ""
            ts = rec.get("timestamp") or ""
            char_id = charmap.get(author.lower()) or charmap.get(rec.get("author_name", "").lower())
            msg_id = f"disc_{dedup}"

            if not dry_run:
                try:
                    conn.execute(
                        "INSERT INTO messages "
                        "(id, scene_id, character_id, author_name, content_original, ts, source, position_order, is_summary) "
                        "VALUES (?, ?, ?, ?, ?, ?, 'discord', ?, 0)",
                        (msg_id, scene_id, char_id, author, content, ts, pos),
                    )
                    stats["inserted"] += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Insert error msg %s: %s", msg_id, exc)
                    stats["errors"] += 1
            else:
                stats["inserted"] += 1  # count would-be inserts in dry-run too

        if not dry_run:
            conn.commit()
            conn.execute(
                "UPDATE scenes SET last_activity_at = strftime('%Y-%m-%d %H:%M:%f', 'now') WHERE id = ?",
                (scene_id,),
            )
            conn.commit()

    conn.close()
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import Discord JSONL into Calliope DB")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "datasets" / "discord_yokai" / "messages_clean.jsonl",
        help="Path to messages_clean.jsonl",
    )
    parser.add_argument("--dry-run", action="store_true", help="Non scrivere nel DB, solo statistiche")
    parser.add_argument("--all-tags", action="store_true", help="Importa anche OOC/system (default: solo IC)")
    parser.add_argument("--limit", type=int, default=None, help="Limita a N righe (per test)")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )

    if not args.input.exists():
        logger.error("Input file not found: %s", args.input)
        return 1

    logger.info("Mode: %s", "DRY-RUN" if args.dry_run else "LIVE IMPORT")
    stats = run(args.input, dry_run=args.dry_run, only_ic=not args.all_tags, limit=args.limit)
    logger.info("Done. stats=%s", stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
