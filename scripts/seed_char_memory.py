#!/usr/bin/env python3
"""Seed char_memory SQLite DB from characters/*.yaml files."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

import yaml
from app.calliope_shell.char_memory import upsert_char, list_chars

CHARS_DIR = Path(__file__).parents[1] / "characters"


def seed() -> int:
    seeded = 0
    for yaml_path in sorted(CHARS_DIR.glob("*.yaml")):
        try:
            raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            if not raw or not isinstance(raw, dict):
                continue
            name = raw.get("name") or raw.get("slug") or yaml_path.stem
            traits = {
                "personality": raw.get("traits", []),
                "quirks": raw.get("quirks", []),
                "flaws": raw.get("flaws", []),
                "speech_pattern": raw.get("speech_pattern", {}).get("notes", ""),
            }
            upsert_char(
                name=name,
                traits=traits,
                last_action=None,
                relationships={},
                last_scene_id=None,
            )
            seeded += 1
            print(f"  ✓ seeded: {name} ({yaml_path.name})")
        except Exception as exc:
            print(f"  ✗ skip {yaml_path.name}: {exc}")
    return seeded


if __name__ == "__main__":
    print("Seeding char_memory DB from characters/*.yaml ...")
    n = seed()
    print(f"\nDone — {n} chars seeded.")
    print("Current DB:", [c["name"] for c in list_chars()])
