"""Unit test per scripts/route_scene.py.

Copre:
  - route_scene() — decision engine (pura, no HTTP)
  - load_config() — YAML validation
  - BlockedContentError — attributi custom
"""
from __future__ import annotations

import pytest
import yaml

from scripts.route_scene import (
    DEFAULT_CONFIG,
    BlockedContentError,
    load_config,
    route_scene,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_score(**kwargs) -> dict:
    """Score con tutti i valori a 0, sovrascrivi solo i campi richiesti."""
    base = {"non_consent": 0, "minors_adjacent": 0, "violence": 0, "explicit": 0}
    base.update(kwargs)
    return base


# ── BlockedContentError ───────────────────────────────────────────────────────

def test_blocked_error_attrs():
    err = BlockedContentError("troppo violento", "non_consent", 4)
    assert err.dimension == "non_consent"
    assert err.score == 4
    assert "troppo violento" in str(err)


# ── route_scene — blocchi hard ────────────────────────────────────────────────

def test_route_scene_block_non_consent():
    with pytest.raises(BlockedContentError) as exc_info:
        route_scene("romantic_fade_to_black", _clean_score(non_consent=3))
    assert exc_info.value.dimension == "non_consent"


def test_route_scene_block_minors_adjacent():
    with pytest.raises(BlockedContentError) as exc_info:
        route_scene("action_combat", _clean_score(minors_adjacent=3))
    assert exc_info.value.dimension == "minors_adjacent"


def test_route_scene_block_threshold_not_reached():
    # nc=2 < 3 → no eccezione
    result = route_scene("action_combat", _clean_score(non_consent=2))
    assert "tier" in result


# ── route_scene — nsfw force (ollama) ────────────────────────────────────────

def test_route_scene_nsfw_force_ollama():
    result = route_scene("action_combat", _clean_score(explicit=2))  # >= nsfw_threshold=2
    assert result["provider"] == "ollama"
    assert "nsfw-forced" in result["rationale"]


def test_route_scene_nsfw_just_below_threshold():
    result = route_scene("action_combat", _clean_score(explicit=1))  # < 2
    # deve usare la matrice, non ollama forzato
    assert result["provider"] == "cerebras"


# ── route_scene — matrix lookup ───────────────────────────────────────────────

def test_route_scene_known_type_action_combat():
    result = route_scene("action_combat", _clean_score())
    assert result["tier"] == "cerebras_workhorse"
    assert result["provider"] == "cerebras"


def test_route_scene_known_type_ooc_meta():
    result = route_scene("ooc_meta", _clean_score())
    assert result["provider"] == "groq"


def test_route_scene_known_type_lore_exposition():
    result = route_scene("lore_exposition", _clean_score())
    assert result["provider"] == "openrouter"


def test_route_scene_unknown_type_falls_back_to_default():
    result = route_scene("unknown_scene_type_xyz", _clean_score())
    # default = cerebras_workhorse
    assert result["tier"] == DEFAULT_CONFIG["matrix"]["default"]["tier"]


# ── route_scene — char_relevance → lora_candidate ────────────────────────────

def test_route_scene_lora_candidate_high():
    result = route_scene("action_combat", _clean_score(), char_relevance="high")
    assert result.get("lora_candidate") is True


def test_route_scene_no_lora_candidate_low():
    result = route_scene("action_combat", _clean_score(), char_relevance="low")
    assert "lora_candidate" not in result


def test_route_scene_nsfw_force_lora_candidate():
    result = route_scene("action_combat", _clean_score(explicit=2), char_relevance="high")
    assert result.get("lora_candidate") is True


def test_route_scene_invalid_char_relevance():
    with pytest.raises(ValueError, match="char_relevance"):
        route_scene("action_combat", _clean_score(), char_relevance="medium")


# ── load_config ───────────────────────────────────────────────────────────────

def test_load_config_valid(tmp_path):
    cfg_data = {
        "matrix": {"default": {"tier": "t", "provider": "p", "model": "m"}},
        "nsfw_threshold": 2,
        "block_thresholds": {"non_consent": 3, "minors_adjacent": 3},
    }
    cfg_path = tmp_path / "routing.yaml"
    cfg_path.write_text(yaml.dump(cfg_data), encoding="utf-8")
    cfg = load_config(str(cfg_path))
    assert cfg["nsfw_threshold"] == 2
    assert "default" in cfg["matrix"]


def test_load_config_missing_matrix_key(tmp_path):
    cfg_data = {
        "nsfw_threshold": 2,
        "block_thresholds": {"non_consent": 3, "minors_adjacent": 3},
        # matrix mancante
    }
    cfg_path = tmp_path / "bad.yaml"
    cfg_path.write_text(yaml.dump(cfg_data), encoding="utf-8")
    with pytest.raises(ValueError, match="matrix"):
        load_config(str(cfg_path))


def test_load_config_missing_default_entry(tmp_path):
    cfg_data = {
        "matrix": {"action_combat": {"tier": "t", "provider": "p", "model": "m"}},
        "nsfw_threshold": 2,
        "block_thresholds": {"non_consent": 3, "minors_adjacent": 3},
    }
    cfg_path = tmp_path / "nodefault.yaml"
    cfg_path.write_text(yaml.dump(cfg_data), encoding="utf-8")
    with pytest.raises(ValueError, match="default"):
        load_config(str(cfg_path))
