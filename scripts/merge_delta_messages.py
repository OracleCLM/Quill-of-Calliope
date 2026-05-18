#!/usr/bin/env python3
import argparse
import glob
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set


def load_existing_ids(output_path: Path) -> Set[str]:
    ids: Set[str] = set()
    if not output_path.exists():
        return ids
    with open(output_path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                ids.add(str(json.loads(line)["message_id"]))
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: skipping malformed line {lineno}: {e}")
    return ids


def read_delta_files(delta_pattern: str) -> List[Dict]:
    json_files = sorted(glob.glob(os.path.join(delta_pattern, "*.json")))
    if not json_files:
        print("No JSON files found in delta directory.")
        return []

    messages: List[Dict] = []
    for fpath in json_files:
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                messages.extend(data)
            else:
                print(f"Warning: expected list in {fpath}, got {type(data).__name__}")
        except Exception as e:
            print(f"Error reading {fpath}: {e}")
    return messages


def transform_message(dce_msg: Dict) -> Dict:
    attachments = dce_msg.get("Attachments", [])
    return {
        "message_id": str(dce_msg["ID"]),
        "timestamp": dce_msg["Timestamp"],
        "author_id": str(dce_msg["Author"]["ID"]),
        "username": dce_msg["Author"]["Name"],
        "nick": dce_msg["Author"].get("Nickname"),
        "content": dce_msg["Content"],
        "attachments": [a["Url"] for a in attachments],
        "channel_id": "",
        "tag": None,
    }


def main():
    parser = argparse.ArgumentParser(description="Merge Discord delta exports into main messages file")
    parser.add_argument("--delta-dir", required=True, help="Directory or glob pattern containing delta JSON files")
    parser.add_argument("--main-output", default="datasets/discord_yokai/messages_clean.jsonl")
    parser.add_argument("--classify", action="store_true", help="Enable classification (not yet implemented)")
    args = parser.parse_args()

    if args.classify:
        print("Classification not implemented.")

    output_path = Path(args.main_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    existing_ids = load_existing_ids(output_path)
    delta_messages = read_delta_files(args.delta_dir)

    if not delta_messages:
        print("No delta messages to process.")
        sys.exit(0)

    new_messages: List[Dict] = []
    duplicates = 0
    for msg in delta_messages:
        mid = str(msg["ID"])
        if mid in existing_ids:
            duplicates += 1
            continue
        new_messages.append(transform_message(msg))
        existing_ids.add(mid)

    if new_messages:
        with open(output_path, "a", encoding="utf-8") as f:
            for m in new_messages:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")

    print(f"{len(new_messages)} new messages added, {duplicates} duplicates skipped.")

    # Sort entire file by timestamp
    all_msgs: List[Dict] = []
    with open(output_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                all_msgs.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Warning: skipping malformed line during sort: {e}")

    all_msgs.sort(key=lambda x: x.get("timestamp", ""))
    with open(output_path, "w", encoding="utf-8") as f:
        for m in all_msgs:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    print(f"Total messages in file: {len(all_msgs)}")


if __name__ == "__main__":
    main()
