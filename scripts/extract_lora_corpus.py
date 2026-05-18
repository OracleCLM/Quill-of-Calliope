#!/usr/bin/env python3
import argparse
import logging
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter
from tqdm import tqdm


def main():
    parser = argparse.ArgumentParser(description="Extract LoRA corpus for character roleplay")
    parser.add_argument("--input", default="datasets/yokai_rpg/messages_clean.jsonl", help="Input JSONL file")
    parser.add_argument("--operator-id", default="Horo", help="Operator player ID")
    parser.add_argument("--top-chars", type=int, default=5, help="Number of top characters to extract")
    parser.add_argument("--context-window", type=int, default=3, help="Number of previous messages in context")
    parser.add_argument("--output", default="datasets/lora/", help="Output directory")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logger = logging.getLogger(__name__)

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Loading messages from {input_path}")
    messages = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in tqdm(f, desc="Loading"):
            if line.strip():
                msg = json.loads(line)
                ts = msg["timestamp"]
                if ts.endswith("Z"):
                    ts = ts[:-1] + "+00:00"
                msg["timestamp"] = datetime.fromisoformat(ts)
                messages.append(msg)

    # Sort by timestamp
    messages.sort(key=lambda x: x["timestamp"])

    # Assign scene_id based on >30min gap
    logger.info("Assigning scene IDs")
    scene_counter = 0
    prev_time = None
    for msg in tqdm(messages, desc="Scenes"):
        current_time = msg["timestamp"]
        if prev_time is None:
            msg["scene_id"] = f"scene_{scene_counter:04d}"
        else:
            if current_time - prev_time > timedelta(minutes=30):
                scene_counter += 1
            msg["scene_id"] = f"scene_{scene_counter:04d}"
        prev_time = current_time

    # Find top N characters for operator_id (IC messages only)
    logger.info(f"Finding top {args.top_chars} characters for {args.operator_id}")
    char_counter: Counter = Counter()
    for msg in messages:
        if (
            msg["player"] == args.operator_id
            and msg["type"] == "IC"
            and msg["character"] is not None
            and msg["message"] is not None
        ):
            char_counter[msg["character"]] += 1

    top_chars = [char for char, _ in char_counter.most_common(args.top_chars)]
    logger.info(f"Top characters: {top_chars}")

    summary: dict[str, int] = {}

    for char_name in tqdm(top_chars, desc="Processing characters"):
        char_slug = re.sub(r"[^a-z0-9-]", "", char_name.lower().replace(" ", "-"))
        output_path = output_dir / f"{char_slug}.jsonl"
        output_chatml_path = output_dir / f"{char_slug}_chatml.jsonl"

        char_messages = [
            msg
            for msg in messages
            if (
                msg["player"] == args.operator_id
                and msg["type"] == "IC"
                and msg["character"] == char_name
                and msg["message"] is not None
            )
        ]

        count_written = 0
        with (
            open(output_path, "w", encoding="utf-8") as f1,
            open(output_chatml_path, "w", encoding="utf-8") as f2,
        ):
            for msg in tqdm(char_messages, desc=f"Context for {char_name}", leave=False):
                # Get up to K previous IC messages in same scene with lower row_idx
                candidates = [
                    m
                    for m in messages
                    if (
                        m["type"] == "IC"
                        and m["message"] is not None
                        and m["scene_id"] == msg["scene_id"]
                        and m["row_idx"] < msg["row_idx"]
                    )
                ]
                # Take last K in chronological order
                candidates.sort(key=lambda x: x["row_idx"])
                context_prev_msgs = candidates[-args.context_window :]

                # Write plain JSONL record
                record = {
                    "text": msg["message"],
                    "char": char_name,
                    "scene_id": msg["scene_id"],
                    "context_prev_msgs": [
                        {"char": m["character"], "player": m["player"], "text": m["message"]}
                        for m in context_prev_msgs
                    ],
                    "timestamp": msg["timestamp"].isoformat(),
                }
                f1.write(json.dumps(record, ensure_ascii=False) + "\n")

                # Build context string for ChatML
                if context_prev_msgs:
                    context_str = "\n".join(
                        f"[{m['character'] or m['player']}]: {m['message']}" for m in context_prev_msgs
                    )
                else:
                    context_str = "(scene start)"

                # Write ChatML record (always 3 messages: system + user + assistant)
                chatml_record = {
                    "messages": [
                        {"role": "system", "content": f"Roleplay as {char_name}."},
                        {"role": "user", "content": context_str},
                        {"role": "assistant", "content": msg["message"]},
                    ]
                }
                f2.write(json.dumps(chatml_record, ensure_ascii=False) + "\n")
                count_written += 1

        summary[char_name] = count_written

    # Log summary
    logger.info("Summary of messages written:")
    for char, count in summary.items():
        logger.info(f"  {char}: {count} messages")


if __name__ == "__main__":
    main()
