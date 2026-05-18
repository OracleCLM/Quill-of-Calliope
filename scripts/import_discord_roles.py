"""Import Discord roles from a markdown table export into JSONL format."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from tqdm import tqdm

# Columns treated as permission flags (all columns except these)
_NON_PERMISSION_COLS = {"name", "position", "id", "mentionable", "tags"}

# Ordered list of permission column names as they appear in the source table
_PERMISSION_COLS = [
    "administrator",
    "mention all",
    "manage guild",
    "manage roles",
    "manage channels",
    "kick members",
    "ban members",
    "webhooks",
]


def _setup_logging(verbose: bool = False) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[handler],
    )


def _parse_bool(value: str) -> bool:
    return value.strip().lower() == "yes"


def _parse_markdown_table(text: str) -> list[dict]:
    """Parse a pipe-delimited markdown table into a list of dicts."""
    lines = [line for line in text.splitlines() if line.strip()]

    # Find header line (first line containing '|')
    header_line = next((ln for ln in lines if "|" in ln), None)
    if header_line is None:
        raise ValueError("No markdown table header found in input file")

    # Parse headers
    headers = [h.strip().lower() for h in header_line.split("|") if h.strip()]
    logging.debug("Parsed headers: %s", headers)

    rows = []
    for line in lines[2:]:  # skip header and separator line
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")]
        # Remove leading/trailing empty strings from split on outer pipes
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]
        if len(cells) != len(headers):
            logging.warning(
                "Row has %d cells, expected %d — skipping: %s",
                len(cells),
                len(headers),
                line,
            )
            continue
        rows.append(dict(zip(headers, cells)))

    return rows


def _row_to_record(row: dict) -> dict:
    """Convert a parsed table row into the output schema."""
    tags = row.get("tags", "")
    is_bot = "bot" in tags.lower()

    permissions_flags = [
        col for col in _PERMISSION_COLS if _parse_bool(row.get(col, "No"))
    ]

    return {
        "name": row["name"],
        "id": row["id"],
        "position": int(row["position"]),
        "mentionable": _parse_bool(row.get("mentionable", "No")),
        "is_bot": is_bot,
        "permissions_flags": permissions_flags,
    }


def import_roles(input_path: Path, output_path: Path) -> int:
    """Parse roles file and write JSONL. Returns count of records written."""
    text = input_path.read_text(encoding="utf-8")
    rows = _parse_markdown_table(text)
    logging.info("Parsed %d data rows from %s", len(rows), input_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with output_path.open("w", encoding="utf-8") as fout:
        for row in tqdm(rows, desc="Writing roles", unit="role"):
            record = _row_to_record(row)
            fout.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

    logging.info("Written %d records to %s", count, output_path)
    return count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import Discord roles markdown table to JSONL"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(
            "/tmp/discord_import/roles/1312211590883442688_1778982271.279325_roles.txt"
        ),
        help="Path to the markdown table roles file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("datasets/discord_yokai/roles.jsonl"),
        help="Output JSONL file path",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable debug logging"
    )
    args = parser.parse_args()

    _setup_logging(args.verbose)

    count = import_roles(args.input, args.output)
    if count < 30:
        logging.error("Only %d roles written — expected >=30", count)
        sys.exit(1)

    logging.info("Done. %d roles imported.", count)


if __name__ == "__main__":
    main()
