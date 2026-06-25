"""Unit test per scripts/import_tupperbox.py (base zai-glm, fix Claude)."""
from __future__ import annotations

from scripts.import_tupperbox import build_group_map, slugify, tupper_to_yaml


# ── slugify ───────────────────────────────────────────────────────────────────

def test_slugify_simple():
    assert slugify("Hello") == "hello"


def test_slugify_spaces():
    assert slugify("Hello World") == "hello-world"


def test_slugify_special_chars():
    # é, &, spaces → un unico run non-alnum → singolo "-"
    assert slugify("Café & Bistro!") == "caf-bistro"


def test_slugify_strip_leading_trailing():
    assert slugify("--test--") == "test"


def test_slugify_empty():
    assert slugify("") == ""


def test_slugify_numbers():
    assert slugify("Test123") == "test123"


def test_slugify_multiple_spaces():
    assert slugify("a  b") == "a-b"


# ── build_group_map ───────────────────────────────────────────────────────────

def test_build_group_map_single():
    assert build_group_map([{"id": 1, "name": "G1"}]) == {1: "G1"}


def test_build_group_map_multiple():
    data = [{"id": 1, "name": "G1"}, {"id": 2, "name": "G2"}]
    assert build_group_map(data) == {1: "G1", 2: "G2"}


def test_build_group_map_empty():
    assert build_group_map([]) == {}


# ── tupper_to_yaml ────────────────────────────────────────────────────────────

def test_tupper_to_yaml_full():
    tupper = {
        "id": 10, "name": "Test", "group_id": 1,
        "description": "desc", "avatar_url": "url",
        "brackets": ["<", ">"], "posts": 5, "last_used": "2023-01-01",
    }
    result = tupper_to_yaml(tupper, {1: "Group A"})
    assert result["name"] == "Test"
    assert result["slug"] == "test"
    assert result["group"] == "Group A"
    assert result["description"] == "desc"
    assert result["avatar_url"] == "url"
    assert result["brackets"] == ["<", ">"]
    assert result["posts_count"] == 5
    assert result["last_used"] == "2023-01-01"
    assert result["tupperbox_id"] == 10


def test_tupper_to_yaml_no_group_id():
    tupper = {"id": 10, "name": "Test", "brackets": []}
    assert tupper_to_yaml(tupper, {})["group"] is None


def test_tupper_to_yaml_unknown_group_id():
    tupper = {"id": 10, "name": "Test", "group_id": 99, "brackets": []}
    assert tupper_to_yaml(tupper, {})["group"] is None


def test_tupper_to_yaml_defaults():
    tupper = {"id": 10, "name": "Test", "brackets": []}
    res = tupper_to_yaml(tupper, {})
    assert res["description"] is None
    assert res["avatar_url"] is None
    assert res["posts_count"] == 0
    assert res["last_used"] is None


def test_tupper_to_yaml_empty_avatar_url_to_none():
    tupper = {"id": 10, "name": "Test", "avatar_url": "", "brackets": []}
    assert tupper_to_yaml(tupper, {})["avatar_url"] is None


# ─────────────────────────────────────────────────────────────────────────────
# Extended tests — setup_logging, main()
# ─────────────────────────────────────────────────────────────────────────────

import json  # noqa: E402
import sys  # noqa: E402

import pytest  # noqa: E402
import yaml  # noqa: E402

from scripts.import_tupperbox import main, setup_logging  # noqa: E402


def test_setup_logging_runs_without_error():
    # Just verify it doesn't raise; reconfiguring basicConfig is idempotent
    setup_logging()


def test_main_missing_input_exits(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["prog", "--input", str(tmp_path / "missing.json")])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


def test_main_writes_yaml_files(monkeypatch, tmp_path):
    data = {
        "groups": [{"id": 1, "name": "GroupA"}],
        "tuppers": [
            {"id": 10, "name": "Alice", "group_id": 1, "brackets": ["<", ">"],
             "description": "A char", "avatar_url": None, "posts": 3, "last_used": "2024-01-01"},
        ],
    }
    input_path = tmp_path / "tuppers.json"
    input_path.write_text(json.dumps(data), encoding="utf-8")
    out_dir = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", [
        "prog", "--input", str(input_path), "--output-dir", str(out_dir)
    ])
    main()
    assert (out_dir / "alice.yaml").exists()
    record = yaml.safe_load((out_dir / "alice.yaml").read_text(encoding="utf-8"))
    assert record["name"] == "Alice"
    assert record["group"] == "GroupA"
    assert record["slug"] == "alice"


def test_main_writes_multiple_tuppers(monkeypatch, tmp_path):
    data = {
        "groups": [],
        "tuppers": [
            {"id": 1, "name": "Aurora", "brackets": ["[", "]"]},
            {"id": 2, "name": "Philip", "brackets": ["{", "}"]},
        ],
    }
    input_path = tmp_path / "t.json"
    input_path.write_text(json.dumps(data), encoding="utf-8")
    out_dir = tmp_path / "chars"
    monkeypatch.setattr(sys, "argv", ["prog", "--input", str(input_path), "--output-dir", str(out_dir)])
    main()
    assert (out_dir / "aurora.yaml").exists()
    assert (out_dir / "philip.yaml").exists()


def test_main_slug_collision_appends_id(monkeypatch, tmp_path):
    data = {
        "groups": [],
        "tuppers": [
            {"id": 1, "name": "Alice", "brackets": ["<", ">"]},
            {"id": 2, "name": "Alice", "brackets": ["[", "]"]},  # same slug → collision
        ],
    }
    input_path = tmp_path / "t.json"
    input_path.write_text(json.dumps(data), encoding="utf-8")
    out_dir = tmp_path / "chars"
    monkeypatch.setattr(sys, "argv", ["prog", "--input", str(input_path), "--output-dir", str(out_dir)])
    main()
    assert (out_dir / "alice.yaml").exists()
    assert (out_dir / "alice-2.yaml").exists()
    record = yaml.safe_load((out_dir / "alice-2.yaml").read_text(encoding="utf-8"))
    assert record["slug"] == "alice-2"


def test_main_empty_tuppers(monkeypatch, tmp_path):
    data = {"groups": [], "tuppers": []}
    input_path = tmp_path / "t.json"
    input_path.write_text(json.dumps(data), encoding="utf-8")
    out_dir = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["prog", "--input", str(input_path), "--output-dir", str(out_dir)])
    main()  # should complete without error
    assert out_dir.exists()
