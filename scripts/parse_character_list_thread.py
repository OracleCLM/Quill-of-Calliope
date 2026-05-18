#!/usr/bin/env python3
import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path


SKIP_KEYWORDS = ["discussion", "ooc", "voting", "poll"]


def parse_threads(
    raw_dir: str,
    channel_id: str,
    output_path: str,
    min_msgs: int = 1,
) -> None:
    json_files = glob.glob(os.path.join(raw_dir, "*.json"))
    if not json_files:
        print(f"No JSON files found in {raw_dir}", file=sys.stderr)
        return

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    threads_found = skipped = written = 0

    with open(out, "w", encoding="utf-8") as f:
        for file_path in json_files:
            try:
                with open(file_path, encoding="utf-8") as fp:
                    data = json.load(fp)
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: {file_path}: {e}", file=sys.stderr)
                continue

            channel = data.get("channel", {})
            if channel.get("type") != "GuildPublicThread":
                continue
            if channel.get("categoryId") != channel_id:
                continue

            threads_found += 1
            thread_name = channel.get("name", "").strip()

            name_lower = thread_name.lower()
            if any(re.search(r"\b" + kw + r"\b", name_lower) for kw in SKIP_KEYWORDS):
                print(f"Skip (non-char): {thread_name}", file=sys.stderr)
                skipped += 1
                continue

            messages = data.get("messages", [])
            msg_count = data.get("messageCount", 0)
            if msg_count < min_msgs or not messages:
                skipped += 1
                continue

            messages = sorted(messages, key=lambda m: m["timestamp"])
            first_msg = messages[0]
            author = first_msg.get("author", {})

            content_blocks = [m["content"].strip() for m in messages if m.get("content", "").strip()]
            sheet_text = "\n\n---\n\n".join(content_blocks)

            all_ts = [m["timestamp"] for m in messages if m.get("timestamp")]
            all_ts += [m["timestampEdited"] for m in messages if m.get("timestampEdited")]
            last_updated = max(all_ts) if all_ts else first_msg["timestamp"]

            record = {
                "char_name": thread_name,
                "thread_id": channel["id"],
                "thread_name": thread_name,
                "author_id": author.get("id", ""),
                "author_username": author.get("name", ""),
                "sheet_text": sheet_text,
                "created_at": first_msg["timestamp"],
                "last_updated": last_updated,
                "msg_count_in_thread": msg_count,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1

    print(f"Threads found: {threads_found}, skipped (non-char/min-msgs): {skipped}, written: {written}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse DCE character list threads into JSONL")
    parser.add_argument("--raw-dir", default="/tmp/discord_import/raw/")
    parser.add_argument("--channel-id", default="1320529977732632697")
    parser.add_argument("--output", default="datasets/discord_yokai/character_sheets_raw.jsonl")
    parser.add_argument("--min-msgs", type=int, default=1)
    args = parser.parse_args()

    try:
        parse_threads(args.raw_dir, args.channel_id, args.output, args.min_msgs)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
