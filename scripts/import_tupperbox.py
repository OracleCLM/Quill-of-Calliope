"""Import Tupperbox characters into Calliope.AI YAML format."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

import yaml
from tqdm import tqdm


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
        stream=sys.stdout,
        encoding="utf-8",
    )


def slugify(name: str) -> str:
    """Convert a name to a lowercase-hyphen slug."""
    # Normalize unicode, remove non-ascii, lowercase, replace spaces/special chars with hyphens
    slug = name.lower()
    # Replace non-alphanumeric chars (except hyphens) with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    # Strip leading/trailing hyphens
    slug = slug.strip("-")
    return slug


def build_group_map(groups: list[dict]) -> dict[int, str]:
    return {g["id"]: g["name"] for g in groups}


def tupper_to_yaml(tupper: dict, group_map: dict[int, str]) -> dict:
    group_id = tupper.get("group_id")
    group_name = group_map.get(group_id) if group_id is not None else None

    return {
        "name": tupper["name"],
        "slug": slugify(tupper["name"]),
        "group": group_name,
        "description": tupper.get("description"),
        "avatar_url": tupper.get("avatar_url") or None,
        "brackets": tupper["brackets"],
        "posts_count": tupper.get("posts", 0),
        "last_used": tupper.get("last_used"),
        "tupperbox_id": tupper["id"],
    }


def main() -> None:
    setup_logging()
    log = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(
        description="Import Tupperbox characters into Calliope.AI YAML format."
    )
    parser.add_argument(
        "--input",
        default="datasets/tupperbox/tuppers.json",
        help="Path to tuppers.json (default: datasets/tupperbox/tuppers.json)",
    )
    parser.add_argument(
        "--output-dir",
        default="characters/private",
        help="Output directory for YAML files (default: characters/private)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    if not input_path.exists():
        log.error("Input file not found: %s", input_path)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    log.info("Output directory: %s", output_dir.resolve())

    with input_path.open(encoding="utf-8") as f:
        data = json.load(f)

    groups = data.get("groups", [])
    tuppers = data.get("tuppers", [])
    group_map = build_group_map(groups)

    log.info("Found %d groups, %d tuppers", len(groups), len(tuppers))

    written = 0
    for tupper in tqdm(tuppers, desc="Importing tuppers", unit="tupper"):
        record = tupper_to_yaml(tupper, group_map)
        slug = record["slug"]
        out_path = output_dir / f"{slug}.yaml"

        # Handle slug collisions by appending tupperbox_id
        if out_path.exists():
            slug_unique = f"{slug}-{tupper['id']}"
            log.warning(
                "Slug collision for '%s', using '%s'", slug, slug_unique
            )
            out_path = output_dir / f"{slug_unique}.yaml"
            record["slug"] = slug_unique

        with out_path.open("w", encoding="utf-8") as f:
            yaml.dump(
                record,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )
        written += 1

    log.info("Done. Wrote %d YAML files to %s", written, output_dir)


if __name__ == "__main__":
    main()
