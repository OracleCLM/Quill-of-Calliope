#!/usr/bin/env python3
"""
R-CALLIOPE-MA-CHAR-SSOT-MIGRATION — migrazione ADDITIVA / NON-DISTRUTTIVA.

Consolida le 3 fonti-personaggio in un'unica SSOT di lettura:
``characters.card_json`` come **Character Card V2**.

Fonti (union per NOME):
  1. YAML  ``characters/*.yaml``  (via characters_service.get_card_v3)
  2. tabella ``character_sheets`` (campo ``content``)
  3. tabella ``characters``       (righe già esistenti — preservate)

VINCOLI nic (ASSOLUTI):
  - si TENGONO TUTTI i personaggi; NON cancellare/rimuovere nulla;
  - i file YAML e la tabella ``character_sheets`` restano INTATTI;
  - merge NON-distruttivo: i campi già popolati in ``card_json`` NON vengono
    sovrascritti; vengono riempiti SOLO i campi vuoti; ``extensions`` ignote
    sono preservate;
  - IDEMPOTENTE: un re-run non crea duplicati né altera ciò già migrato.

Uso:
    python3 scripts/migrate_chars_to_ssot.py            # DB reale (data/calliope.db o $CALLIOPE_DB_PATH)
    python3 scripts/migrate_chars_to_ssot.py --db /tmp/copy.db --dry-run
    python3 scripts/migrate_chars_to_ssot.py --no-backup   # salta backup (test)

Output: report JSON su stdout (created/merged/unchanged + count pre/post).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
import tarfile
import time
import datetime as _dt
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Repo-root su sys.path
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.db import characters as chardb  # noqa: E402

DEFAULT_DB = _REPO_ROOT / "data" / "calliope.db"
CHARS_DIR = _REPO_ROOT / "characters"
BACKUP_ROOT = _REPO_ROOT / "data" / "backups"


# --------------------------------------------------------------------------- #
# Backup
# --------------------------------------------------------------------------- #
def make_backup(db_path: Path, runid: str) -> Path:
    """Copia DB (+WAL/SHM) e tar di characters/ in data/backups/migration_<runid>/."""
    dest = BACKUP_ROOT / f"migration_{runid}"
    dest.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-wal", "-shm"):
        src = Path(str(db_path) + suffix)
        if src.is_file():
            shutil.copy2(src, dest / src.name)
    if CHARS_DIR.is_dir():
        tar_path = dest / "characters.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(CHARS_DIR, arcname="characters")
    return dest


def _json_safe(obj: Any) -> Any:
    """Coerce ricorsivamente a primitivi JSON-serializzabili.

    YAML carica date/datetime come oggetti Python: li serializziamo a ISO-str
    cosi' ``json.dumps`` non esplode (non-distruttivo: stesso valore leggibile).
    """
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (_dt.date, _dt.datetime, _dt.time)):
        return obj.isoformat()
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


# --------------------------------------------------------------------------- #
# Source readers — costruiscono Card V2 candidate (campi assenti = vuoti)
# --------------------------------------------------------------------------- #
def _candidate_from_v3(name: str, v3: Dict[str, Any], *, kind: str,
                       image_path: str) -> Dict[str, Any]:
    """Mappa un dict V3 (da YAML) in una Card V2 candidate.

    I campi-prompt noti vanno in ``data.*``; tutto il resto delle extensions
    YAML confluisce in ``data.extensions.calliope`` insieme a kind/image_path.
    """
    card = chardb.empty_card_v2(name)
    data = card["data"]
    for f in ("description", "personality", "scenario", "first_mes",
              "mes_example", "system_prompt", "post_history_instructions"):
        val = v3.get(f)
        if isinstance(val, str):
            data[f] = val
    cb = v3.get("character_book")
    if cb:
        data["character_book"] = cb
    tags = v3.get("tags")
    if isinstance(tags, list):
        data["tags"] = list(tags)

    # extensions.calliope: campi Calliope-specifici dal YAML
    yaml_ext = v3.get("extensions") or {}
    cal: Dict[str, Any] = {}
    if isinstance(yaml_ext, dict):
        # speech_pattern / backstory / aliases / id ecc. finiscono qui da from_legacy_yaml
        for k in ("speech_pattern", "backstory", "discord_aliases", "char_memory_ref"):
            if k in yaml_ext:
                cal[k] = yaml_ext[k]
        # preserva l'intero blob legacy YAML sotto chiave dedicata (non-distruttivo)
        cal["yaml_legacy"] = yaml_ext
    cal["kind"] = kind
    if image_path:
        cal["image_path"] = image_path
    data["extensions"]["calliope"] = _json_safe(cal)
    return _json_safe(card)


def _candidate_from_sheet(name: str, content: str) -> Dict[str, Any]:
    """Mappa una riga character_sheets in Card V2 candidate.

    L'unico contenuto strutturato disponibile è ``content`` → ``data.description``.
    Niente campi inventati.
    """
    card = chardb.empty_card_v2(name)
    if content:
        card["data"]["description"] = content
    card["data"]["extensions"]["calliope"]["kind"] = "npc"
    card["data"]["extensions"]["calliope"]["source"] = "character_sheets"
    return card


def collect_sources(conn: sqlite3.Connection) -> Dict[str, Dict[str, Any]]:
    """Raccoglie le candidate per nome dalle 3 fonti.

    Precedenza per il *contenuto* candidate: YAML > character_sheets.
    (La fonte ``characters`` esistente NON è una candidate: è il merge-target.)
    Ritorna ``{name: candidate_card_v2}``.
    """
    from app.calliope_shell import characters_service as cs

    candidates: Dict[str, Dict[str, Any]] = {}

    # --- character_sheets (priorità più bassa) ---
    rows = conn.execute(
        "SELECT character_name, content FROM character_sheets "
        "WHERE character_name IS NOT NULL "
        "ORDER BY character_name, position_order"
    ).fetchall()
    seen_sheet: set = set()
    for r in rows:
        nm = r[0]
        if not nm or nm in seen_sheet:
            continue
        seen_sheet.add(nm)
        candidates[nm] = _candidate_from_sheet(nm, r[1] or "")

    # --- YAML (priorità più alta: sovrascrive la candidate sheet) ---
    chars_path = CHARS_DIR
    stems: set = set()
    for p in chars_path.glob("*.draft.yaml"):
        stems.add(p.name[: -len(".draft.yaml")])
    for p in chars_path.glob("*.canon.yaml"):
        stems.add(p.name[: -len(".canon.yaml")])
    for stem in stems:
        v3 = cs.get_card_v3(stem)
        if not v3:
            continue
        nm = v3.get("name") or stem
        kind = "npc"
        legacy = v3.get("extensions") or {}
        # tipo dal legacy YAML: type pc/player -> player
        t = (legacy.get("type") or "").lower() if isinstance(legacy, dict) else ""
        if t in ("pc", "player"):
            kind = "player"
        candidates[nm] = _candidate_from_v3(nm, v3, kind=kind, image_path="")

    return candidates


# --------------------------------------------------------------------------- #
# Non-destructive merge
# --------------------------------------------------------------------------- #
def _is_empty(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, str):
        return val.strip() == ""
    if isinstance(val, (list, dict)):
        return len(val) == 0
    return False


def merge_into(existing: Dict[str, Any], candidate: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Riempie SOLO i campi vuoti di ``existing`` con quelli di ``candidate``.

    Preserva ogni valore già presente e le extensions ignote.
    Ritorna ``(merged_card, changed)``.
    """
    merged = json.loads(json.dumps(existing))  # deep copy
    merged.setdefault("spec", chardb.CARD_V2_SPEC)
    merged.setdefault("spec_version", chardb.CARD_V2_VERSION)
    edata = merged.setdefault("data", {})
    cdata = candidate.get("data", {})
    changed = False

    # name: riempi solo se vuoto
    if _is_empty(edata.get("name")) and not _is_empty(cdata.get("name")):
        edata["name"] = cdata["name"]
        changed = True

    for f in ("description", "personality", "scenario", "first_mes",
              "mes_example", "system_prompt", "post_history_instructions",
              "creator_notes"):
        if _is_empty(edata.get(f)) and not _is_empty(cdata.get(f)):
            edata[f] = cdata[f]
            changed = True

    if _is_empty(edata.get("tags")) and not _is_empty(cdata.get("tags")):
        edata["tags"] = cdata["tags"]
        changed = True

    if _is_empty(edata.get("character_book")) and not _is_empty(cdata.get("character_book")):
        edata["character_book"] = cdata["character_book"]
        changed = True

    # extensions.calliope: merge chiave-per-chiave, riempi solo i vuoti
    ext = edata.setdefault("extensions", {})
    cal = ext.setdefault("calliope", {})
    ccal = (cdata.get("extensions") or {}).get("calliope", {})
    for k, v in ccal.items():
        if k not in cal or _is_empty(cal.get(k)):
            if not _is_empty(v) or k not in cal:
                cal[k] = v
                changed = True

    return merged, changed


# --------------------------------------------------------------------------- #
# Migration driver
# --------------------------------------------------------------------------- #
def _existing_names(conn: sqlite3.Connection) -> set:
    return {r[0] for r in conn.execute("SELECT name FROM characters").fetchall()}


def migrate(conn: sqlite3.Connection) -> Dict[str, Any]:
    candidates = collect_sources(conn)
    existing = _existing_names(conn)

    report = {
        "created": [], "merged": [], "unchanged": [],
        "sources": {}, "pre": {}, "post": {},
    }

    # union pre = distinct names su 3 fonti
    sheet_names = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT character_name FROM character_sheets "
            "WHERE character_name IS NOT NULL"
        ).fetchall()
    }
    yaml_names = {
        nm for nm, c in candidates.items()
        if (c["data"]["extensions"]["calliope"].get("source") != "character_sheets")
    }
    union_pre = set(existing) | sheet_names | yaml_names
    report["sources"] = {
        "characters_rows_pre": len(existing),
        "character_sheets_distinct": len(sheet_names),
        "yaml_candidates": len(yaml_names),
        "candidates_total": len(candidates),
        "union_distinct_pre": len(union_pre),
    }

    for name, candidate in candidates.items():
        if name in existing:
            card = chardb.load_card_v2(conn, name) or chardb.empty_card_v2(name)
            merged, changed = merge_into(card, candidate)
            chardb.save_card_v2(conn, name, merged)
            if changed:
                report["merged"].append(name)
            else:
                report["unchanged"].append(name)
        else:
            kind = candidate["data"]["extensions"]["calliope"].get("kind", "npc")
            chardb.add_character(conn, name=name, kind=kind, card_json=None)
            chardb.save_card_v2(conn, name, candidate)
            report["created"].append(name)
            existing.add(name)

    post_names = _existing_names(conn)
    post_with_card = conn.execute(
        "SELECT COUNT(*) FROM characters WHERE card_json IS NOT NULL"
    ).fetchone()[0]
    report["post"] = {
        "characters_rows_post": len(post_names),
        "characters_with_card_json": post_with_card,
        "union_distinct_pre": len(union_pre),
        "no_loss": union_pre.issubset(post_names),
        "missing_from_post": sorted(union_pre - post_names),
    }
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None, help="path DB (default: $CALLIOPE_DB_PATH o data/calliope.db)")
    ap.add_argument("--dry-run", action="store_true", help="rollback finale, nessuna scrittura persistita")
    ap.add_argument("--no-backup", action="store_true", help="salta il backup (solo test/copia)")
    args = ap.parse_args()

    db_path = Path(args.db) if args.db else Path(
        os.environ.get("CALLIOPE_DB_PATH") or DEFAULT_DB
    )

    runid = time.strftime("%Y%m%d_%H%M%S")
    backup_dir: Optional[Path] = None
    if not args.no_backup and not args.dry_run:
        backup_dir = make_backup(db_path, runid)

    conn = sqlite3.connect(str(db_path))
    try:
        report = migrate(conn)
        if args.dry_run:
            conn.rollback()
    finally:
        conn.close()

    report["runid"] = runid
    report["db_path"] = str(db_path)
    report["backup_dir"] = str(backup_dir) if backup_dir else None
    report["dry_run"] = args.dry_run
    # report compatto (liste -> conteggi + sample)
    summary = {
        "runid": runid,
        "db_path": str(db_path),
        "backup_dir": str(backup_dir) if backup_dir else None,
        "dry_run": args.dry_run,
        "sources": report["sources"],
        "post": report["post"],
        "counts": {
            "created": len(report["created"]),
            "merged": len(report["merged"]),
            "unchanged": len(report["unchanged"]),
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if report["post"]["no_loss"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
