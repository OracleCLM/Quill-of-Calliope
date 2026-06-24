"""Unit test per scripts/build_lore_index.py — _extract_char_lore e _extract_scene_lore."""
from __future__ import annotations

import yaml

from scripts.build_lore_index import _extract_char_lore, _extract_scene_lore


# ── _extract_char_lore ────────────────────────────────────────────────────────

def test_char_invalid_yaml(tmp_path):
    p = tmp_path / "char.yaml"
    p.write_text("name: [invalid", encoding="utf-8")
    assert _extract_char_lore(p) == []


def test_char_non_dict_yaml(tmp_path):
    p = tmp_path / "char.yaml"
    p.write_text("- item1\n- item2", encoding="utf-8")
    assert _extract_char_lore(p) == []


def test_char_minimal_data_no_docs(tmp_path):
    p = tmp_path / "char.yaml"
    p.write_text(yaml.dump({"name": "Bob"}), encoding="utf-8")
    assert _extract_char_lore(p) == []


def test_char_short_backstory_skipped(tmp_path):
    p = tmp_path / "char.yaml"
    p.write_text(yaml.dump({"name": "Bob", "backstory": "Short"}), encoding="utf-8")
    assert _extract_char_lore(p) == []


def test_char_long_backstory(tmp_path):
    p = tmp_path / "char.yaml"
    data = {"name": "Alice", "backstory": "She was born in a forest and lived there for many years."}
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_char_lore(p)
    assert len(result) == 1
    assert result[0]["id"] == "char_backstory_alice"
    assert result[0]["text"] == "Alice — backstory: She was born in a forest and lived there for many years."
    assert result[0]["meta"]["type"] == "backstory"


def test_char_identity_basic(tmp_path):
    p = tmp_path / "char.yaml"
    data = {"name": "Alice", "race": "Elf", "class": "Mage", "gender": "Female"}
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_char_lore(p)
    assert len(result) == 1
    assert result[0]["id"] == "char_identity_alice"
    assert result[0]["text"] == "Alice is a Female Elf Mage"


def test_char_identity_with_details(tmp_path):
    p = tmp_path / "char.yaml"
    data = {
        "name": "Alice", "race": "Human", "class": "Warrior", "gender": "Male",
        "origin": "London", "age": "30",
        "traits": ["Brave", "Strong", "Loud", "Fast", "Smart", "Wise"],
    }
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_char_lore(p)
    text = result[0]["text"]
    assert "Alice is a Male Human Warrior" in text
    assert "from London" in text
    assert "age 30" in text
    assert "Traits: Brave, Strong, Loud, Fast, Smart" in text
    assert "Wise" not in text  # solo 5 traits


def test_char_relationships(tmp_path):
    p = tmp_path / "char.yaml"
    data = {"name": "Alice", "relationships": {"Bob": "Friend", "Charlie": "Enemy"}}
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_char_lore(p)
    assert len(result) == 1
    assert result[0]["id"] == "char_rels_alice"
    assert "Alice relationships:" in result[0]["text"]
    assert "Bob: Friend" in result[0]["text"]


def test_char_behavior_role(tmp_path):
    p = tmp_path / "char.yaml"
    data = {"name": "Alice", "behavior_pattern": {"role": "Leader"}}
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_char_lore(p)
    assert len(result) == 1
    assert result[0]["id"] == "char_role_alice"


def test_char_combined_docs(tmp_path):
    p = tmp_path / "char.yaml"
    data = {
        "name": "Alice",
        "backstory": "She was born in a forest and lived there for many years.",
        "race": "Elf", "class": "Ranger", "gender": "Female",
        "relationships": {"Bob": "Ally"},
        "behavior_pattern": {"role": "Scout"},
    }
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_char_lore(p)
    assert len(result) == 4
    ids = {doc["id"] for doc in result}
    assert "char_backstory_alice" in ids
    assert "char_identity_alice" in ids
    assert "char_rels_alice" in ids
    assert "char_role_alice" in ids


# ── _extract_scene_lore ───────────────────────────────────────────────────────

def test_scene_invalid_yaml(tmp_path):
    p = tmp_path / "scene.yaml"
    p.write_text("title: [invalid", encoding="utf-8")
    assert _extract_scene_lore(p) == []


def test_scene_non_dict_yaml(tmp_path):
    p = tmp_path / "scene.yaml"
    p.write_text(yaml.dump(["list", "item"]), encoding="utf-8")
    assert _extract_scene_lore(p) == []


def test_scene_missing_summary(tmp_path):
    p = tmp_path / "scene.yaml"
    p.write_text(yaml.dump({"title": "Event"}), encoding="utf-8")
    assert _extract_scene_lore(p) == []


def test_scene_short_summary_skipped(tmp_path):
    p = tmp_path / "scene.yaml"
    p.write_text(yaml.dump({"title": "Event", "summary": "Short"}), encoding="utf-8")
    assert _extract_scene_lore(p) == []


def test_scene_valid_basic(tmp_path):
    p = tmp_path / "scene.yaml"
    data = {"title": "The Battle", "summary": "A great battle took place at dawn."}
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_scene_lore(p)
    assert len(result) == 1
    assert result[0]["id"] == "scene_lore_scene"
    assert result[0]["text"] == "Scene 'The Battle': A great battle took place at dawn."
    assert result[0]["meta"]["source"] == "scene"
    assert result[0]["meta"]["type"] == "event"


def test_scene_with_participants(tmp_path):
    p = tmp_path / "scene.yaml"
    data = {
        "title": "The Meeting",
        "summary": "They discussed the future of the realm in great detail.",
        "participants": ["Alice", "Bob"],
    }
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_scene_lore(p)
    assert len(result) == 1
    assert "(participants: Alice, Bob)" in result[0]["text"]
    assert result[0]["meta"]["participants"] == "Alice,Bob"


def test_scene_long_text_truncated(tmp_path):
    p = tmp_path / "scene.yaml"
    data = {"title": "Long Event", "summary": "x" * 600}
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_scene_lore(p)
    assert len(result) == 1
    assert len(result[0]["text"]) == 500


def test_scene_custom_id(tmp_path):
    p = tmp_path / "scene.yaml"
    data = {"scene_id": "act1_scene1", "title": "Start", "summary": "The story begins here for real."}
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_scene_lore(p)
    assert len(result) == 1
    assert result[0]["id"] == "scene_lore_act1_scene1"
    assert result[0]["meta"]["scene_id"] == "act1_scene1"
