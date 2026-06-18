"""GAP-58: test per load_character_yaml e load_scene_yaml."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import yaml

from app.calliope_shell.scene_model import (
    CharacterCard,
    SceneChat,
    load_character_yaml,
    load_scene_yaml,
)


# ── helpers ───────────────────────────────────────────────────────────────────


def _write_char_yaml(path: Path, data: dict) -> Path:
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


def _write_scene_yaml(path: Path, data: dict) -> Path:
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


# ── load_character_yaml ───────────────────────────────────────────────────────


def test_load_char_yaml_returns_character_card(tmp_path):
    f = _write_char_yaml(tmp_path / "aurora.yaml", {"name": "Aurora"})
    result = load_character_yaml(f)
    assert isinstance(result, CharacterCard)


def test_load_char_yaml_name_preserved(tmp_path):
    f = _write_char_yaml(tmp_path / "aurora.yaml", {"name": "Aurora"})
    card = load_character_yaml(f)
    assert card.name == "Aurora"


def test_load_char_yaml_missing_name_fallback(tmp_path):
    f = _write_char_yaml(tmp_path / "anon.yaml", {})
    card = load_character_yaml(f)
    assert isinstance(card, CharacterCard)


def test_load_char_yaml_description_preserved(tmp_path):
    f = _write_char_yaml(tmp_path / "mao.yaml", {
        "name": "Mao", "description": "Una strega misteriosa"
    })
    card = load_character_yaml(f)
    assert card.description == "Una strega misteriosa"


def test_load_char_yaml_personality_preserved(tmp_path):
    f = _write_char_yaml(tmp_path / "kira.yaml", {
        "name": "Kira", "personality": "impulsiva e coraggiosa"
    })
    card = load_character_yaml(f)
    assert card.personality == "impulsiva e coraggiosa"


def test_load_char_yaml_empty_file_does_not_raise(tmp_path):
    f = tmp_path / "empty.yaml"
    f.write_text("", encoding="utf-8")
    card = load_character_yaml(f)
    assert isinstance(card, CharacterCard)


# ── load_scene_yaml ───────────────────────────────────────────────────────────


def test_load_scene_yaml_returns_scene_chat(tmp_path):
    f = _write_scene_yaml(tmp_path / "sc1.yaml", {"title": "Scena 1"})
    result = load_scene_yaml(f)
    assert isinstance(result, SceneChat)


def test_load_scene_yaml_title_as_name(tmp_path):
    f = _write_scene_yaml(tmp_path / "sc2.yaml", {"title": "La Foresta"})
    scene = load_scene_yaml(f)
    assert scene.name == "La Foresta"


def test_load_scene_yaml_stem_fallback_for_title(tmp_path):
    f = _write_scene_yaml(tmp_path / "foresta_oscura.yaml", {})
    scene = load_scene_yaml(f)
    assert "foresta_oscura" in scene.name


def test_load_scene_yaml_scene_id_from_data(tmp_path):
    f = _write_scene_yaml(tmp_path / "sc3.yaml", {"scene_id": "id-42", "title": "T"})
    scene = load_scene_yaml(f)
    assert scene.id == "id-42"


def test_load_scene_yaml_scene_id_fallback_to_stem(tmp_path):
    f = _write_scene_yaml(tmp_path / "my_scene.yaml", {"title": "T"})
    scene = load_scene_yaml(f)
    assert scene.id == "my_scene"


def test_load_scene_yaml_participants_as_members(tmp_path):
    f = _write_scene_yaml(tmp_path / "sc4.yaml", {
        "title": "T", "participants": ["Aurora", "Mao"]
    })
    scene = load_scene_yaml(f)
    assert "Aurora" in scene.members
    assert "Mao" in scene.members


def test_load_scene_yaml_non_list_participants_ignored(tmp_path):
    f = _write_scene_yaml(tmp_path / "sc5.yaml", {
        "title": "T", "participants": "not-a-list"
    })
    scene = load_scene_yaml(f)
    assert scene.members == []


def test_load_scene_yaml_is_readonly(tmp_path):
    f = _write_scene_yaml(tmp_path / "sc6.yaml", {"title": "T"})
    scene = load_scene_yaml(f)
    assert scene.read_only is True


def test_load_scene_yaml_created_from_timestamp(tmp_path):
    f = _write_scene_yaml(tmp_path / "sc7.yaml", {
        "title": "T", "timestamp_start": "2024-01-01"
    })
    scene = load_scene_yaml(f)
    assert scene.created == "2024-01-01"


def test_load_scene_yaml_empty_file_does_not_raise(tmp_path):
    f = tmp_path / "empty_scene.yaml"
    f.write_text("", encoding="utf-8")
    scene = load_scene_yaml(f)
    assert isinstance(scene, SceneChat)
