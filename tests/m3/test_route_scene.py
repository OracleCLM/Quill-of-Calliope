"""Tests for scripts/route_scene.py — 10 scenarios."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from route_scene import BlockedContentError, DEFAULT_CONFIG, load_config, route_scene  # noqa: E402

CLEAN = {"nudity_explicit": 0, "violence_gore": 0, "non_consent": 0, "minors_adjacent": 0}


def test_action_combat_clean():
    r = route_scene("action_combat", CLEAN, config=DEFAULT_CONFIG)
    assert r["tier"] == "cerebras_workhorse"
    assert r["provider"] == "cerebras"
    assert r["model"] == "qwen-3-235b-a22b-instruct-2507"
    assert "action_combat" in r["rationale"]


def test_lore_exposition_clean():
    r = route_scene("lore_exposition", CLEAN, config=DEFAULT_CONFIG)
    assert r["provider"] == "openrouter"
    assert r["tier"] == "openrouter_reasoning"


def test_romantic_below_threshold():
    # nudity=1 < threshold 2 → no Ollama force → groq_fast
    r = route_scene("romantic_fade_to_black", {**CLEAN, "nudity_explicit": 1}, config=DEFAULT_CONFIG)
    assert r["tier"] == "groq_fast"
    assert r["provider"] == "groq"


def test_violence_forces_ollama():
    # violence=2 >= threshold → force Ollama regardless of scene_type
    r = route_scene("action_combat", {**CLEAN, "violence_gore": 2}, config=DEFAULT_CONFIG)
    assert r["tier"] == "ollama_uncensored"
    assert r["provider"] == "ollama"
    assert "[nsfw-forced]" in r["rationale"]
    assert "nsfw_max=2" in r["rationale"]


def test_nsfw_explicit_nudity3():
    r = route_scene("nsfw_explicit", {**CLEAN, "nudity_explicit": 3}, config=DEFAULT_CONFIG)
    assert r["provider"] == "ollama"
    assert r["model"] == "dolphin-mistral-24b"


def test_block_non_consent():
    with pytest.raises(BlockedContentError) as exc:
        route_scene("action_combat", {**CLEAN, "non_consent": 3}, config=DEFAULT_CONFIG)
    assert exc.value.dimension == "non_consent"
    assert exc.value.score == 3


def test_block_minors_adjacent():
    with pytest.raises(BlockedContentError) as exc:
        route_scene("lore_exposition", {**CLEAN, "minors_adjacent": 3}, config=DEFAULT_CONFIG)
    assert exc.value.dimension == "minors_adjacent"
    assert exc.value.score == 3


def test_custom_config(tmp_path):
    custom = {
        "matrix": {
            "action_combat": {"tier": "groq_fast", "provider": "groq", "model": "llama-3.3-70b-versatile"},
            "default":        {"tier": "cerebras_workhorse", "provider": "cerebras", "model": "qwen-3-235b-a22b-instruct-2507"},
            "nsfw_explicit":  {"tier": "ollama_uncensored", "provider": "ollama", "model": "dolphin-mistral-24b"},
        },
        "nsfw_threshold": 2,
        "block_thresholds": {"non_consent": 3, "minors_adjacent": 3},
    }
    cfg_path = tmp_path / "custom.yaml"
    cfg_path.write_text(yaml.dump(custom))
    loaded = load_config(str(cfg_path))
    assert loaded["matrix"]["action_combat"]["tier"] == "groq_fast"
    r = route_scene("action_combat", CLEAN, config=loaded)
    assert r["tier"] == "groq_fast"


def test_char_relevance_high():
    r = route_scene("action_combat", CLEAN, char_relevance="high", config=DEFAULT_CONFIG)
    assert r["tier"] == "cerebras_workhorse"
    assert r.get("lora_candidate") is True


def test_default_fallback():
    r = route_scene("totally_unknown_type", CLEAN, config=DEFAULT_CONFIG)
    assert r["tier"] == "cerebras_workhorse"
    assert "totally_unknown_type" in r["rationale"]


def test_block_takes_priority_over_ollama_force():
    # non_consent=3 → block even though it would also trigger nsfw_force
    with pytest.raises(BlockedContentError):
        route_scene("nsfw_explicit", {**CLEAN, "non_consent": 3, "nudity_explicit": 3}, config=DEFAULT_CONFIG)
