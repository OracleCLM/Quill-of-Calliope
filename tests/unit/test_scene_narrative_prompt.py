"""Unit test per scripts/scene_narrative.py — build_scene_prompt (pura)."""
from __future__ import annotations

from scripts.scene_narrative import build_scene_prompt


def test_first_scene_contains_location_and_chars():
    result = build_scene_prompt(1, "A dark forest.", "Forest", "Alice, Bob", "")
    assert "[Location: Forest]" in result
    assert "[Characters: Alice, Bob]" in result
    assert "Scene 1:" in result
    assert "A dark forest." in result


def test_first_scene_ends_with_instruction():
    result = build_scene_prompt(1, "Seed", "Loc", "Char", "")
    assert result.endswith("Write 2-3 paragraphs in third person, fantasy RP style.")


def test_first_scene_with_state_context():
    result = build_scene_prompt(1, "Start.", "Tavern", "Hero", "", state_context="Combat: Active")
    assert "\nCombat: Active\n" in result
    assert "[Location: Tavern]" in result


def test_first_scene_no_state_no_extra_newlines():
    result = build_scene_prompt(1, "Seed", "Loc", "Char", "", state_context="")
    # state_block vuoto → nessun blocco \n...\n extra
    assert "\n\n" not in result.split("[Characters:")[0]  # niente doppio newline prima della lista chars


def test_continuation_scene_structure():
    prev = "The dragon roared.\n\nThe knight drew his sword."
    result = build_scene_prompt(2, "", "", "", prev)
    assert "[Continuation of previous scene]" in result
    assert "[Previous scene excerpt]:" in result
    assert "The dragon roared." in result
    assert "Scene 2 (continue the narrative):" in result
    assert "The knight drew his sword." in result


def test_continuation_excerpt_truncated_at_200():
    long_text = "A" * 300
    result = build_scene_prompt(2, "", "", "", long_text)
    assert "A" * 200 in result  # excerpt presente
    assert "[Previous scene excerpt]:" in result


def test_continuation_last_paragraph_used():
    prev = "First para.\n\nSecond para.\n\nThird para."
    result = build_scene_prompt(3, "", "", "", prev)
    assert "Scene 3 (continue the narrative):\nThird para." in result


def test_continuation_empty_prev_text():
    result = build_scene_prompt(2, "", "", "", "")
    assert "Scene 2 (continue the narrative):" in result
    assert "[Previous scene excerpt]:" in result


def test_continuation_with_state_context():
    result = build_scene_prompt(2, "", "", "", "Text.", state_context="Weather: Rain")
    assert "[Continuation of previous scene]\nWeather: Rain\n" in result
