#!/usr/bin/env python3
"""Quill of Calliope — Excel RP history importer M1.

Pipeline:
1. Load .xlsx → DataFrame pandas
2. Normalize character names (strip HP markers like "75/100%")
3. Decode HTML entities (html.unescape)
4. Tag IC/OOC/system
5. Sort by timestamp ascending
6. Write datasets/yokai_rpg/messages_clean.jsonl (32598 records)
7. Filter Horo IC → datasets/yokai_rpg/operator_style_corpus.jsonl
8. Temporal scene detection (30min gap, >=10 msgs) → raw scene data JSON
9. Write scenes/raw_scene_data.json for post-processing MCP step

Usage:
    python import_excel_history.py /tmp/calliope_import/Yokai.xlsx
    python import_excel_history.py /tmp/calliope_import/Yokai.xlsx --output ~/Scrivania/Quill_of_Calliope
"""
from __future__ import annotations

import argparse
import html
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

OPERATOR_PLAYER = "Horo"
SCENE_GAP_MINUTES = 30
SCENE_MIN_MESSAGES = 10
TOP_CHARS = [
    "NARRATOR", "Aurora", "Philip Annabelle", "Koibo", "Cassandra Blythe",
    "Mirko", "Saturn", "Pdor", "Peaches", "Arianna", "Viola", "Clover",
    "Kikyo", "Azu Blythe", "Nikita", "Syvis", "Ira", "Yan Qing",
    "Filomena", "Silver",
]


def normalize_character_name(name: str | None) -> str | None:
    if name is None or pd.isna(name):
        return None
    name = str(name).strip()
    # strip HP markers: "Philip Annabelle 75/100%" → "Philip Annabelle"
    name = re.sub(r'\s+\d+/\d+%?\s*$', '', name).strip()
    return name


def safe_str(val: Any) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    return html.unescape(str(val))


def classify_row(row: pd.Series) -> str:
    if pd.notna(row.get("system message")):
        return "system"
    if pd.notna(row.get("character")):
        return "IC"
    return "OOC"


def ts_to_iso(ts: Any) -> str | None:
    if ts is None or (isinstance(ts, float) and pd.isna(ts)):
        return None
    try:
        return pd.Timestamp(ts).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return str(ts)


def load_and_clean(xlsx_path: Path) -> pd.DataFrame:
    log.info("Loading %s...", xlsx_path)
    df = pd.read_excel(xlsx_path, engine="openpyxl")
    log.info("Loaded %d rows × %d cols", len(df), len(df.columns))

    df["character"] = df["character"].apply(normalize_character_name)
    df["type"] = df.apply(classify_row, axis=1)
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["row_idx"] = df.index
    log.info("Sorted by timestamp. IC=%d OOC=%d system=%d",
             (df["type"] == "IC").sum(),
             (df["type"] == "OOC").sum(),
             (df["type"] == "system").sum())
    return df


def write_messages_clean(df: pd.DataFrame, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8") as f:
        for _, row in df.iterrows():
            orig_msg = row.get("original message")
            record = {
                "row_idx": int(row["row_idx"]),
                "timestamp": ts_to_iso(row.get("timestamp")),
                "player": safe_str(row.get("player")),
                "character": row["character"],
                "type": row["type"],
                "message": safe_str(row.get("message")),
                "original_message": safe_str(orig_msg) if pd.notna(orig_msg) else None,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    log.info("messages_clean.jsonl → %d records", count)
    return count


def write_operator_corpus(df: pd.DataFrame, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mask = (df["type"] == "IC") & (df["player"] == OPERATOR_PLAYER)
    subset = df[mask].copy()
    count = 0
    with output_path.open("w", encoding="utf-8") as f:
        for _, row in subset.iterrows():
            record = {
                "row_idx": int(row["row_idx"]),
                "timestamp": ts_to_iso(row.get("timestamp")),
                "player": OPERATOR_PLAYER,
                "character": row["character"],
                "type": "IC",
                "message": safe_str(row.get("message")),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    log.info("operator_style_corpus.jsonl → %d records (Horo IC)", count)
    return count


def detect_scenes(df: pd.DataFrame) -> list[dict]:
    ic_df = df[df["type"] == "IC"].copy()
    scenes = []
    current_msgs: list[dict] = []
    prev_ts = None
    scene_idx = 0

    for _, row in ic_df.iterrows():
        ts = row.get("timestamp")
        if prev_ts is not None and pd.notna(ts) and pd.notna(prev_ts):
            gap_min = (ts - prev_ts).total_seconds() / 60
            if gap_min > SCENE_GAP_MINUTES and current_msgs:
                scenes.append(_finalize_scene(scene_idx, current_msgs))
                scene_idx += 1
                current_msgs = []

        current_msgs.append({
            "row_idx": int(row["row_idx"]),
            "timestamp": ts_to_iso(ts),
            "player": safe_str(row.get("player")),
            "character": row["character"],
            "message": safe_str(row.get("message")),
        })
        prev_ts = ts

    if current_msgs:
        scenes.append(_finalize_scene(scene_idx, current_msgs))

    valid = [s for s in scenes if s["message_count"] >= SCENE_MIN_MESSAGES]
    log.info("Scene detection: %d total → %d valid (>=%d msgs)",
             len(scenes), len(valid), SCENE_MIN_MESSAGES)
    return valid


def _finalize_scene(idx: int, msgs: list[dict]) -> dict:
    participants = sorted({m["character"] for m in msgs if m["character"]})
    players = sorted({m["player"] for m in msgs if m["player"]})
    return {
        "scene_idx": idx,
        "scene_id": f"scene_{idx:03d}",
        "timestamp_start": msgs[0]["timestamp"],
        "timestamp_end": msgs[-1]["timestamp"],
        "message_count": len(msgs),
        "participants": participants,
        "players": players,
        "first_msg_excerpt": (msgs[0]["message"] or "")[:200],
        "last_msg_excerpt": (msgs[-1]["message"] or "")[:200],
        "messages_sample": _sample_messages(msgs, n=5),
    }


def _sample_messages(msgs: list[dict], n: int = 5) -> list[dict]:
    if len(msgs) <= n:
        return msgs
    step = len(msgs) // n
    return [msgs[i * step] for i in range(n)]


def extract_char_samples(df: pd.DataFrame, chars: list[str], n_sample: int = 40) -> dict[str, list[dict]]:
    result = {}
    for char in chars:
        char_df = df[(df["type"] == "IC") & (df["character"] == char)].copy()
        if len(char_df) == 0:
            log.warning("No messages for char: %s", char)
            continue
        # mix: 60% random + 40% recency
        n_recent = max(1, int(n_sample * 0.4))
        n_random = n_sample - n_recent
        recent = char_df.tail(n_recent)
        pool = char_df.iloc[:-n_recent] if len(char_df) > n_recent else char_df
        random_sample = pool.sample(min(n_random, len(pool)), random_state=42)
        combined = pd.concat([random_sample, recent]).drop_duplicates().sort_values("timestamp")
        samples = []
        for _, row in combined.iterrows():
            samples.append({
                "timestamp": ts_to_iso(row.get("timestamp")),
                "player": safe_str(row.get("player")),
                "message": safe_str(row.get("message")),
            })
        result[char] = samples
        log.info("  %s: %d messages sampled (total: %d)", char, len(samples), len(char_df))
    return result


def extract_narrator_messages(df: pd.DataFrame) -> list[str]:
    narrator_df = df[(df["type"] == "IC") & (df["character"] == "NARRATOR")].copy()
    msgs = []
    for _, row in narrator_df.iterrows():
        msg = safe_str(row.get("message"))
        if msg:
            msgs.append(msg)
    log.info("Extracted %d NARRATOR messages for lore analysis", len(msgs))
    return msgs


def main() -> None:
    parser = argparse.ArgumentParser(description="Quill of Calliope Excel history importer M1")
    parser.add_argument("input_file", type=Path, help="Path to .xlsx")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/home/nic/Scrivania/Quill_of_Calliope"),
        help="Project root directory",
    )
    args = parser.parse_args()

    if not args.input_file.exists():
        log.error("Input file not found: %s", args.input_file)
        sys.exit(1)

    base = args.output
    datasets_dir = base / "datasets" / "yokai_rpg"
    scenes_dir = base / "scenes"
    datasets_dir.mkdir(parents=True, exist_ok=True)
    scenes_dir.mkdir(parents=True, exist_ok=True)

    # Step 1-4: load, normalize, classify, sort
    df = load_and_clean(args.input_file)

    # Step 5: messages_clean.jsonl
    count = write_messages_clean(df, datasets_dir / "messages_clean.jsonl")
    assert count == 32598, f"Expected 32598 records, got {count}"

    # Step 6: operator_style_corpus.jsonl
    op_count = write_operator_corpus(df, datasets_dir / "operator_style_corpus.jsonl")
    log.info("Horo IC corpus: %d messages", op_count)

    # Step 7: scene detection → raw scene data
    scenes = detect_scenes(df)
    raw_scenes_path = datasets_dir / "scenes_raw.json"
    with raw_scenes_path.open("w", encoding="utf-8") as f:
        json.dump(scenes, f, ensure_ascii=False, indent=2)
    log.info("scenes_raw.json → %d scenes (>= %d msgs)", len(scenes), SCENE_MIN_MESSAGES)

    # Step 8: char samples → raw char data
    char_samples = extract_char_samples(df, TOP_CHARS, n_sample=40)
    raw_chars_path = datasets_dir / "char_samples_raw.json"
    with raw_chars_path.open("w", encoding="utf-8") as f:
        json.dump(char_samples, f, ensure_ascii=False, indent=2)
    log.info("char_samples_raw.json → %d chars", len(char_samples))

    # Step 9: narrator messages → raw lore data
    narrator_msgs = extract_narrator_messages(df)
    raw_narrator_path = datasets_dir / "narrator_messages_raw.json"
    with raw_narrator_path.open("w", encoding="utf-8") as f:
        json.dump(narrator_msgs, f, ensure_ascii=False, indent=2)
    log.info("narrator_messages_raw.json → %d messages", len(narrator_msgs))

    print("\n=== M1 Phase 1 Complete ===")
    print(f"messages_clean.jsonl: {count} records")
    print(f"operator_style_corpus.jsonl: {op_count} records (Horo IC)")
    print(f"scenes detected: {len(scenes)} (>= {SCENE_MIN_MESSAGES} msgs)")
    print(f"char samples: {len(char_samples)} chars")
    print(f"narrator messages: {len(narrator_msgs)}")
    print("\nNext: MCP cerebras analysis for chars, scenes, lore.")


if __name__ == "__main__":
    main()
