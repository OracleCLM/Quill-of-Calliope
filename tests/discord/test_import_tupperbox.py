"""Smoke tests for scripts/import_tupperbox.py."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Minimal sample data (mirrors real tuppers.json structure)
# ---------------------------------------------------------------------------

SAMPLE_GROUP = {"id": 1702045, "name": "Grimm Troupe", "avatar": None, "description": None, "tag": None}

SAMPLE_TUPPER = {
    "id": 152262786,
    "name": "Grimm",
    "brackets": ["Grimm:", ""],
    "avatar_url": "https://cdn.tupperbox.app/pfp/603341648360898581/Mpea1D0KFDgKxt3l.webp",
    "avatar": "Mpea1D0KFDgKxt3l",
    "banner": None,
    "posts": 1,
    "show_brackets": False,
    "birthday": None,
    "description": "Otherworldly Creature\nGrimm is an imposing being.",
    "tag": None,
    "nick": None,
    "created_at": None,
    "group_id": 1702045,
    "last_used": "2025-04-26T00:23:25.449Z",
}

SAMPLE_DATA = {"groups": [SAMPLE_GROUP], "tuppers": [SAMPLE_TUPPER]}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run_import(input_path: Path, output_dir: Path) -> None:
    """Run the importer directly (no subprocess) via importlib."""
    import importlib.util
    import sys

    script = Path(__file__).parent.parent.parent / "scripts" / "import_tupperbox.py"
    spec = importlib.util.spec_from_file_location("import_tupperbox", script)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]

    # Patch sys.argv so argparse uses our temp paths
    old_argv = sys.argv[:]
    sys.argv = [
        "import_tupperbox.py",
        "--input",
        str(input_path),
        "--output-dir",
        str(output_dir),
    ]
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        mod.main()
    finally:
        sys.argv = old_argv


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_single_tupper_round_trip() -> None:
    """Write one tupper to disk and verify the YAML round-trips correctly."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_file = tmp_path / "tuppers.json"
        output_dir = tmp_path / "output"

        input_file.write_text(json.dumps(SAMPLE_DATA), encoding="utf-8")
        run_import(input_file, output_dir)

        yaml_files = list(output_dir.glob("*.yaml"))
        assert len(yaml_files) == 1, f"Expected 1 YAML file, got {len(yaml_files)}"

        with yaml_files[0].open(encoding="utf-8") as f:
            record = yaml.safe_load(f)

        # Core fields
        assert record["name"] == "Grimm"
        assert record["slug"] == "grimm"
        assert record["group"] == "Grimm Troupe"
        assert record["tupperbox_id"] == 152262786
        assert record["brackets"] == ["Grimm:", ""]
        assert record["posts_count"] == 1
        assert record["last_used"] == "2025-04-26T00:23:25.449Z"
        assert record["avatar_url"].startswith("https://")
        assert "Otherworldly" in record["description"]


def test_null_group_id() -> None:
    """Tupper with group_id=None should produce group: null in YAML."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tupper_no_group = dict(SAMPLE_TUPPER, group_id=None, name="Orphan", id=9999999)
        data = {"groups": [SAMPLE_GROUP], "tuppers": [tupper_no_group]}

        input_file = tmp_path / "tuppers.json"
        output_dir = tmp_path / "output"
        input_file.write_text(json.dumps(data), encoding="utf-8")
        run_import(input_file, output_dir)

        yaml_files = list(output_dir.glob("*.yaml"))
        assert len(yaml_files) == 1
        with yaml_files[0].open(encoding="utf-8") as f:
            record = yaml.safe_load(f)
        assert record["group"] is None


def test_slug_format() -> None:
    """Slugs should be lowercase-hyphen, no special characters."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tupper_special = dict(
            SAMPLE_TUPPER,
            name='SCP-682 "Hard to Destroy Reptile"',
            id=152262784,
        )
        data = {"groups": [SAMPLE_GROUP], "tuppers": [tupper_special]}

        input_file = tmp_path / "tuppers.json"
        output_dir = tmp_path / "output"
        input_file.write_text(json.dumps(data), encoding="utf-8")
        run_import(input_file, output_dir)

        yaml_files = list(output_dir.glob("*.yaml"))
        assert len(yaml_files) == 1
        slug = yaml_files[0].stem
        assert slug == slug.lower()
        assert " " not in slug
        assert '"' not in slug
