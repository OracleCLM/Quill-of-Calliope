"""Import ChatGPT export JSON into Quill of Calliope dataset.

ChatGPT export format (Settings > Data Controls > Export):
  conversations.json — array of conversation objects, each with
  {title, mapping: {node_id: {message: {author: {role}, content: {parts}}}}}

This script extracts user/assistant turns, classifies RP-related ones,
and outputs JSONL compatible with build_chromadb_index.py.

Usage:
    python scripts/import_chatgpt_history.py --input conversations.json --output datasets/chatgpt/messages.jsonl
    python scripts/import_chatgpt_history.py --input conversations.json --output datasets/chatgpt/messages.jsonl --rp-only
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

RP_KEYWORDS = {
    "roleplay", "rp", "character", "scene", "fantasy", "yokai",
    "aurora", "kikyo", "narrative", "in character", "write as",
    "you are", "continue the story", "describe", "action",
    "dice", "roll", "combat", "spell", "tavern", "guild",
}

CATEGORIES = {
    "brainstorming": {"brainstorm", "idea", "what if", "how about", "suggest", "concept"},
    "translation": {"translate", "traduc", "italian", "english", "inglese", "italiano"},
    "drafting": {"write", "draft", "scene", "describe", "narrate", "continue"},
    "lore": {"lore", "world", "magic system", "faction", "geography", "history", "religion"},
}


def _is_rp_related(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in RP_KEYWORDS)


def _categorize(text: str) -> str:
    lower = text.lower()
    for cat, keywords in CATEGORIES.items():
        if any(kw in lower for kw in keywords):
            return cat
    return "general"


def _extract_text(content: dict | None) -> str:
    if not content:
        return ""
    parts = content.get("parts", [])
    texts = []
    for p in parts:
        if isinstance(p, str):
            texts.append(p)
        elif isinstance(p, dict) and p.get("text"):
            texts.append(p["text"])
    return "\n".join(texts)


def parse_conversations(data: list[dict], rp_only: bool = False) -> list[dict]:
    records = []
    for conv in data:
        title = conv.get("title", "")
        create_time = conv.get("create_time")
        conv_id = conv.get("id", "")
        mapping = conv.get("mapping", {})

        for node_id, node in mapping.items():
            msg = node.get("message")
            if not msg:
                continue
            author = msg.get("author", {})
            role = author.get("role", "")
            if role not in ("user", "assistant"):
                continue
            content = msg.get("content", {})
            text = _extract_text(content)
            if not text or len(text.strip()) < 10:
                continue

            if rp_only and not _is_rp_related(text):
                continue

            record = {
                "source": "chatgpt",
                "conversation_id": conv_id,
                "conversation_title": title,
                "node_id": node_id,
                "role": role,
                "text": text.strip(),
                "category": _categorize(text),
                "rp_related": _is_rp_related(text),
                "timestamp": msg.get("create_time") or create_time,
                "char_count": len(text),
            }
            records.append(record)

    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import ChatGPT export into Calliope dataset")
    parser.add_argument("--input", required=True, help="Path to conversations.json")
    parser.add_argument("--output", required=True, help="Output JSONL path")
    parser.add_argument("--rp-only", action="store_true", help="Only include RP-related messages")
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        logger.error("Input file not found: %s", input_path)
        return 1

    try:
        with input_path.open(encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON: %s", e)
        return 1

    if not isinstance(data, list):
        logger.error("Expected array of conversations, got %s", type(data).__name__)
        return 1

    records = parse_conversations(data, rp_only=args.rp_only)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    rp_count = sum(1 for r in records if r["rp_related"])
    cats = {}
    for r in records:
        cats[r["category"]] = cats.get(r["category"], 0) + 1

    print(f"Imported {len(records)} messages from {len(data)} conversations")
    print(f"  RP-related: {rp_count}/{len(records)}")
    print(f"  Categories: {json.dumps(cats, indent=2)}")
    print(f"  Output: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
