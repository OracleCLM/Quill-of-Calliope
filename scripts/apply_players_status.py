#!/usr/bin/env python3
"""
Annotate Discord messages with player status using fuzzy matching on player names and aliases.
"""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, cast

import yaml
import rapidfuzz.fuzz
import rapidfuzz.process


def load_players_mapping(players_yaml: Path) -> Dict[str, str]:
    """
    Load players and aliases from YAML and return a mapping from candidate string to player name.
    """
    try:
        data = yaml.safe_load(players_yaml.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"Error: Players YAML file not found: {players_yaml}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error: Failed to parse YAML file {players_yaml}: {e}", file=sys.stderr)
        sys.exit(1)

    mapping: Dict[str, str] = {}
    players = data.get("players", [])
    if not isinstance(players, list):
        print('Error: Expected "players" to be a list in YAML.', file=sys.stderr)
        sys.exit(1)

    for player in players:
        if not isinstance(player, dict) or "name" not in player:
            continue
        name = cast(str, player["name"])
        aliases = player.get("aliases", [])
        if not isinstance(aliases, list):
            continue
        # Add name itself
        mapping[name] = name
        # Add all aliases
        for alias in aliases:
            if isinstance(alias, str) and alias.strip():
                mapping[alias.strip()] = name

    return mapping


def process_messages(
    messages_file: Path,
    output_file: Path,
    players_mapping: Dict[str, str],
    threshold: float,
    dry_run: bool,
) -> Dict[str, Any]:
    """
    Process messages, annotate with player status, and return stats.
    """
    all_candidates = list(players_mapping.keys())
    stats: Dict[str, Any] = {
        "total": 0,
        "active": 0,
        "unknown": 0,
        "player_counts": {},
    }

    output_path = output_file.resolve()
    temp_file = None
    if not dry_run:
        temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".jsonl",
            dir=output_path.parent,
            delete=False,
            encoding="utf-8",
        )

    try:
        with messages_file.open("r", encoding="utf-8") as f_in:
            for line in f_in:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    print(f"Warning: Skipping invalid JSON line: {line}", file=sys.stderr)
                    continue

                stats["total"] += 1
                match_target = msg.get("author_nick") or msg.get("author_name")
                if not match_target:
                    msg["player_status"] = "unknown"
                    msg["player_match_name"] = None
                    msg["player_match_score"] = 0.0
                    stats["unknown"] += 1
                else:
                    best = rapidfuzz.process.extractOne(
                        match_target,
                        all_candidates,
                        scorer=rapidfuzz.fuzz.WRatio,
                        score_cutoff=threshold * 100,
                    )
                    if best is not None:
                        candidate_str, score_raw = best[0], best[1]
                        player_name = players_mapping[candidate_str]
                        msg["player_status"] = "active"
                        msg["player_match_name"] = player_name
                        msg["player_match_score"] = round(score_raw / 100.0, 4)
                        stats["active"] += 1
                        stats["player_counts"][player_name] = (
                            stats["player_counts"].get(player_name, 0) + 1
                        )
                    else:
                        msg["player_status"] = "unknown"
                        msg["player_match_name"] = None
                        msg["player_match_score"] = 0.0
                        stats["unknown"] += 1

                if not dry_run:
                    assert temp_file is not None
                    temp_file.write(json.dumps(msg, ensure_ascii=False) + "\n")

    except FileNotFoundError:
        print(f"Error: Messages file not found: {messages_file}", file=sys.stderr)
        sys.exit(1)
    except PermissionError as e:
        print(f"Error: Permission denied when reading/writing files: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Unexpected error during message processing: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        if temp_file:
            temp_file.close()

    # Perform atomic write
    if not dry_run and temp_file:
        try:
            shutil.move(temp_file.name, output_path)
        except Exception as e:
            print(f"Error: Failed to move temporary file to output: {e}", file=sys.stderr)
            # Clean up temp file on failure
            Path(temp_file.name).unlink(missing_ok=True)
            sys.exit(1)

    return stats


def print_stats(stats: Dict[str, Any]) -> None:
    """Print processing statistics."""
    total = stats["total"]
    active = stats["active"]
    unknown = stats["unknown"]
    match_rate = (active / total * 100) if total > 0 else 0.0

    print(f"Total messages: {total}")
    print(f"Active matches: {active}")
    print(f"Unknown: {unknown}")
    print(f"Match rate: {match_rate:.2f}%")

    print("\nPer-player message counts:")
    sorted_players = sorted(
        stats["player_counts"].items(), key=lambda x: x[1], reverse=True
    )
    for player, count in sorted_players:
        print(f"  {player}: {count}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Annotate Discord messages with player status."
    )
    parser.add_argument(
        "--players-yaml",
        type=Path,
        default=Path(".planning/players_active.yaml"),
        help="YAML file with player names and aliases (default: .planning/players_active.yaml)",
    )
    parser.add_argument(
        "--messages",
        type=Path,
        default=Path("datasets/discord_yokai/messages_clean.jsonl"),
        help=(
            "Input JSONL file with Discord messages "
            "(default: datasets/discord_yokai/messages_clean.jsonl)"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("datasets/discord_yokai/messages_clean.jsonl"),
        help=(
            "Output JSONL file "
            "(default: datasets/discord_yokai/messages_clean.jsonl)"
        ),
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="Matching threshold between 0 and 1 (default: 0.7)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print stats without writing output file",
    )

    args = parser.parse_args()

    # Validate threshold
    if not 0.0 <= args.threshold <= 1.0:
        print("Error: --threshold must be between 0.0 and 1.0", file=sys.stderr)
        sys.exit(1)

    # Validate input files exist
    if not args.players_yaml.exists():
        print(
            f"Error: Players YAML file does not exist: {args.players_yaml}",
            file=sys.stderr,
        )
        sys.exit(1)
    if not args.messages.exists():
        print(
            f"Error: Messages file does not exist: {args.messages}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load players mapping
    players_mapping = load_players_mapping(args.players_yaml)

    # Process messages
    stats = process_messages(
        messages_file=args.messages,
        output_file=args.output,
        players_mapping=players_mapping,
        threshold=args.threshold,
        dry_run=args.dry_run,
    )

    # Print stats
    print_stats(stats)


if __name__ == "__main__":
    main()
