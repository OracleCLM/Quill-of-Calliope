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
