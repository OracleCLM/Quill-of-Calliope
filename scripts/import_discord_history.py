"""Import Discord Channel Exporter (DCE) JSON exports into Calliope.AI dataset.

Usage:
    python scripts/import_discord_history.py --input-dir /tmp/discord_import/raw/ --output datasets/discord_yokai/messages_clean.jsonl
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    tqdm = None  # type: ignore[assignment]

try:
    import yaml as _yaml
    from rapidfuzz import fuzz as _fuzz
    from rapidfuzz import process as _rfprocess
    _FUZZY_AVAILABLE = True
except ImportError:  # pragma: no cover
    _FUZZY_AVAILABLE = False

logger = logging.getLogger(__name__)

SYSTEM_TYPES = {"ThreadCreated", "ChannelPinnedMessage"}
OOC_PREFIXES = ("(", "[")


def _load_player_index(yaml_path: Path, threshold: float = 0.7) -> dict | None:
    """Build fuzzy player index from players_active.yaml. Returns None if unavailable."""
    if not _FUZZY_AVAILABLE or not yaml_path.exists():
        return None
    try:
        with yaml_path.open(encoding="utf-8") as fh:
            data = _yaml.safe_load(fh)
    except Exception:  # noqa: BLE001
        return None
    candidates: list[tuple[str, str]] = []  # (candidate_string, canonical_name)
    for player in data.get("players", []):
        name = player.get("name", "")
        if name:
            candidates.append((name, name))
            for alias in player.get("aliases", []):
                if alias:
                    candidates.append((alias, name))
    return {"candidates": candidates, "threshold": threshold}


def _apply_player_status(record: dict, player_index: dict | None) -> dict:
    """Add player_status and player_match_name fields to a message record."""
    if player_index is None:
        record["player_status"] = None
        record["player_match_name"] = None
        return record
    match_target = record.get("author_nick") or record.get("author_name") or ""
    candidates = player_index["candidates"]
    threshold = player_index["threshold"]
    choice_strings = [c[0] for c in candidates]
    result = _rfprocess.extractOne(
        match_target, choice_strings, scorer=_fuzz.WRatio,
        score_cutoff=threshold * 100,
    )
    if result:
        matched_candidate, score, idx = result
        record["player_status"] = "active"
        record["player_match_name"] = candidates[idx][1]
        record["player_match_score"] = round(score / 100.0, 3)
    else:
        record["player_status"] = "unknown"
        record["player_match_name"] = None
        record["player_match_score"] = 0.0
    return record


def _load_tupper_names(tuppers_path: Path) -> set[str]:
    """Load known Tupperbox proxy names from tuppers.json.

    Returns an empty set if the file is missing or malformed.
    """
    if not tuppers_path.exists():
        logger.warning("tuppers.json not found at %s — Tupperbox detection degraded", tuppers_path)
        return set()
    try:
        with tuppers_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        return {t["name"] for t in data.get("tuppers", [])}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to parse tuppers.json: %s", exc)
        return set()


def _classify_tag(msg_type: str, content: str) -> str:
    """Return 'system', 'OOC', or 'IC' for a message."""
    if msg_type in SYSTEM_TYPES:
        return "system"
    stripped = content.strip()
    if stripped.startswith(OOC_PREFIXES):
        return "OOC"
    return "IC"


def parse_channel(data: dict, tupper_names: set) -> list[dict]:
    """Parse a single DCE channel export dict into a list of clean message dicts.

    Args:
        data: Parsed DCE JSON for one channel file.
        tupper_names: Set of known Tupperbox proxy author names.

    Returns:
        List of message dicts matching the Calliope messages_clean schema.
    """
    guild = data.get("guild", {})
    channel = data.get("channel", {})

    guild_id: str = str(guild.get("id", ""))
    channel_id: str = str(channel.get("id", ""))
    channel_name: str = channel.get("name", "")
    channel_type: str = channel.get("type", "")

    # parent_channel_id: only set for threads
    parent_channel_id: str | None = None
    if channel_type == "GuildPublicThread":
        parent_channel_id = channel.get("categoryId") or None

    records: list[dict] = []
    for msg in data.get("messages", []):
        author = msg.get("author", {})
        is_bot: bool = bool(author.get("isBot", False))
        author_name: str = author.get("name", "")
        msg_type: str = msg.get("type", "Default")
        content: str = msg.get("content", "")

        # Tupperbox proxy: bot account whose name is in the known tupper set,
        # or (fallback) any bot when tupper_names is empty.
        tupperbox_proxy: bool = is_bot and (
            author_name in tupper_names if tupper_names else True
        )

        # Reference (reply)
        reference = msg.get("reference") or {}
        reply_to: str | None = reference.get("messageId") or None

        record: dict = {
            "message_id": str(msg.get("id", "")),
            "timestamp": msg.get("timestamp", ""),
            "timestamp_edited": msg.get("timestampEdited"),
            "channel_id": channel_id,
            "channel_name": channel_name,
            "parent_channel_id": parent_channel_id,
            "guild_id": guild_id,
            "author_id": str(author.get("id", "")),
            "author_name": author_name,
            "author_nick": author.get("nickname") or None,
            "is_bot": is_bot,
            "content": content,
            "msg_type": msg_type,
            "tag": _classify_tag(msg_type, content),
            "reply_to": reply_to,
            "tupperbox_proxy": tupperbox_proxy,
            "attachments": msg.get("attachments", []),
            "reactions": msg.get("reactions", []),
        }
        records.append(record)

    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import Discord Channel Exporter JSON files into Calliope.AI dataset.",
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        type=Path,
        help="Directory containing DCE JSON export files.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output JSONL file path (e.g. datasets/discord_yokai/messages_clean.jsonl).",
    )
    parser.add_argument(
        "--tuppers",
        type=Path,
        default=Path("datasets/tupperbox/tuppers.json"),
        help="Path to tuppers.json (default: datasets/tupperbox/tuppers.json).",
    )
    parser.add_argument(
        "--players-yaml",
        dest="players_yaml",
        type=Path,
        default=Path(".planning/players_active.yaml"),
        help="Optional players YAML for player_status tagging (default: .planning/players_active.yaml).",
    )
    args = parser.parse_args(argv)

    # Logging setup — explicit UTF-8 handler to avoid encoding issues on Windows/CI
    handler = logging.StreamHandler(sys.stdout)
    handler.setStream(open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False))  # noqa: SIM115, PTH123
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[handler],
    )

    input_dir: Path = args.input_dir
    output_path: Path = args.output
    tuppers_path: Path = args.tuppers

    if not input_dir.is_dir():
        logger.error("--input-dir does not exist or is not a directory: %s", input_dir)
        return 1

    json_files = sorted(input_dir.glob("*.json"))
    if not json_files:
        logger.warning("No JSON files found in %s", input_dir)
        return 0

    tupper_names = _load_tupper_names(tuppers_path)
    logger.info("Loaded %d tupper names", len(tupper_names))

    player_index = _load_player_index(args.players_yaml)
    if player_index:
        logger.info("Loaded player index: %d candidates from %s", len(player_index["candidates"]), args.players_yaml)
    else:
        logger.info("No player index loaded — player_status will be null")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_messages = 0
    file_iter = tqdm(json_files, desc="Channels", unit="file") if tqdm else json_files

    with output_path.open("w", encoding="utf-8") as out_fh:
        for json_path in file_iter:
            try:
                with json_path.open(encoding="utf-8") as fh:
                    data = json.load(fh)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping %s — parse error: %s", json_path.name, exc)
                continue

            records = parse_channel(data, tupper_names)
            for rec in records:
                _apply_player_status(rec, player_index)
                out_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            total_messages += len(records)
            logger.info("  %s → %d messages", json_path.name, len(records))

    logger.info("Done. Total messages written: %d → %s", total_messages, output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
