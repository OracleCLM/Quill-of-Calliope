"""Ripara i YAML malformati con quote interne non escapate (CALLIOPE_DATA_DEBT.md).

ROOT-CAUSE: il generatore draft emetteva titoli/partecipanti con doppi apici senza
escape, es. `"Garaph "Gabby""`. Questo script re-quota quei valori usando apici singoli.

SAFE: legge come testo, applica regex sulla struttura nota (YAML block mapping),
ricrea con yaml.safe_load+yaml.safe_dump per validare il risultato prima di salvare.

Usage:
    python scripts/repair_yaml_quotes.py [--scenes-dir scenes/] [--dry-run]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


def _fix_line(line: str) -> str:
    """Riempie una singola riga: se ha doppi apici interni, cambia in apici singoli."""

    def _requery(prefix: str, content: str) -> str:
        if '"' not in content:
            return f'{prefix}"{content}"'
        if "'" not in content:
            return f"{prefix}'{content}'"
        # Entrambi i tipi di quote: usa doppi apici con escape
        escaped = content.replace('"', '\\"')
        return f'{prefix}"{escaped}"'

    # Lista YAML: `  - "content"`  (qualsiasi indentazione)
    m = re.match(r'^(\s+- )"(.+)"$', line)
    if m and '"' in m.group(2):
        return _requery(m.group(1), m.group(2))

    # Campi scalar generici: `<indent><key>: "content"`
    m = re.match(r'^(\s*\w[\w\s_-]*: )"(.+)"$', line)
    if m and '"' in m.group(2):
        return _requery(m.group(1), m.group(2))

    return line


def _repair_text(text: str) -> str:
    lines = text.splitlines(keepends=True)
    return "".join(_fix_line(ln.rstrip("\n")) + ("\n" if ln.endswith("\n") else "") for ln in lines)


def _verify(text: str) -> bool:
    try:
        yaml.safe_load(text)
        return True
    except yaml.YAMLError:
        return False


def repair_file(path: Path, dry_run: bool) -> tuple[str, str]:
    """Ritorna (status, detail) dove status è 'ok'/'skip'/'failed'/'error'."""
    original = path.read_text(encoding="utf-8")

    if _verify(original):
        return "skip", "già valido"

    fixed = _repair_text(original)

    if not _verify(fixed):
        return "failed", "riparazione non sufficiente"

    if not dry_run:
        path.write_text(fixed, encoding="utf-8")
    return "ok", "riparato"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Ripara YAML malformati (quote interne)")
    parser.add_argument("--scenes-dir", default="scenes", help="directory YAML")
    parser.add_argument("--chars-dir", default="characters", help="directory char YAML")
    parser.add_argument("--dry-run", action="store_true", help="simula senza scrivere")
    args = parser.parse_args(argv)

    dirs = []
    if Path(args.scenes_dir).is_dir():
        dirs.append(Path(args.scenes_dir))
    if Path(args.chars_dir).is_dir():
        dirs.append(Path(args.chars_dir))

    if not dirs:
        print("[ERRORE] Nessuna directory trovata.", file=sys.stderr)
        sys.exit(1)

    counts = {"ok": 0, "skip": 0, "failed": 0, "error": 0}
    for d in dirs:
        for yf in sorted(d.glob("*.yaml")):
            try:
                status, detail = repair_file(yf, dry_run=args.dry_run)
                counts[status] += 1
                if status != "skip":
                    prefix = "[DRY-RUN]" if args.dry_run and status == "ok" else f"[{status.upper()}]"
                    print(f"{prefix} {yf.name}: {detail}")
            except Exception as exc:
                counts["error"] += 1
                print(f"[ERROR] {yf.name}: {exc}", file=sys.stderr)

    mode = " (dry-run)" if args.dry_run else ""
    print(f"\nRisultato{mode}: {counts['ok']} riparati, {counts['skip']} già validi, "
          f"{counts['failed']} non riparabili, {counts['error']} errori")


if __name__ == "__main__":
    main()
