"""Tests for scripts/scene_narrative.py — M3 narrative chain."""

import sys
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))

from scene_narrative import (  # noqa: E402
    DEFAULT_CONFIG,
    generate_scene_chain,
    write_narrative_index,
)

_MOCK_ROUTING = {
    "tier": "cerebras_workhorse",
    "provider": "cerebras",
    "model": "qwen-3-235b-a22b-instruct-2507",
    "rationale": "test",
}

_NSFW_SCORE: Dict[str, int] = {
    "nudity_explicit": 0,
    "violence_gore": 0,
    "non_consent": 0,
    "minors_adjacent": 0,
}


def _make_args(tmp_path: Path, n_scenes: int = 3, scene_types: str = "action_combat,lore_exposition,romantic_fade_to_black") -> SimpleNamespace:
    return SimpleNamespace(
        seed="A warrior stands at the gate.",
        n_scenes=n_scenes,
        scene_types=scene_types,
        char_list="",
        location="Kingdom of Yokai",
        output_dir=tmp_path,
        nsfw_score=_NSFW_SCORE.copy(),
        gateway_url="http://localhost:8766",
    )


def test_chain_3_scenes_mock(tmp_path: Path) -> None:
    """3-scene chain with mocked dispatch: files created + narrative_index exists."""
    with patch("scene_narrative.dispatch_to_tier", return_value="Generated text."), \
         patch("scene_narrative.route_scene", return_value=_MOCK_ROUTING):
        args = _make_args(tmp_path, n_scenes=3)
        stats = generate_scene_chain(args, DEFAULT_CONFIG, args.nsfw_score)

    expected_files = [
        "scene_01_action_combat.md",
        "scene_02_lore_exposition.md",
        "scene_03_romantic_fade_to_black.md",
    ]
    for fname in expected_files:
        assert (tmp_path / fname).exists(), f"Missing {fname}"

    write_narrative_index(tmp_path, stats, args.seed, args.location, "", "2026-05-17T00:00:00")
    assert (tmp_path / "narrative_index.md").exists()
    assert len(stats) == 3


def test_scene_type_cycling(tmp_path: Path) -> None:
    """2 scenes with 1 scene_type → both use same type."""
    with patch("scene_narrative.dispatch_to_tier", return_value="Generated text."), \
         patch("scene_narrative.route_scene", return_value=_MOCK_ROUTING):
        args = _make_args(tmp_path, n_scenes=2, scene_types="action_combat")
        stats = generate_scene_chain(args, DEFAULT_CONFIG, args.nsfw_score)

    assert stats[0]["scene_type"] == "action_combat"
    assert stats[1]["scene_type"] == "action_combat"


def test_prev_excerpt_in_continuation(tmp_path: Path) -> None:
    """Scene 2 prompt contains text from scene 1."""
    first_scene_text = "First scene text. " * 50
    with patch(
        "scene_narrative.dispatch_to_tier",
        side_effect=[first_scene_text, "Second scene text."],
    ) as mock_dispatch, \
         patch("scene_narrative.route_scene", return_value=_MOCK_ROUTING):
        args = _make_args(tmp_path, n_scenes=2, scene_types="action_combat,lore_exposition")
        generate_scene_chain(args, DEFAULT_CONFIG, args.nsfw_score)

    # Second call args: dispatch_to_tier(tier_name, prompt, config=..., gateway_url=..., timeout=...)
    second_call = mock_dispatch.call_args_list[1]
    if second_call.args and len(second_call.args) >= 2:
        prompt_arg = second_call.args[1]
    else:
        prompt_arg = second_call.kwargs.get("prompt", "")

    assert "First scene text." in prompt_arg


def _is_gateway_up() -> bool:
    try:
        urllib.request.urlopen("http://localhost:8766/health", timeout=2)
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _is_gateway_up(), reason="Gateway not running")
def test_real_single_scene(tmp_path: Path) -> None:
    """Real single-scene generation (skipped if gateway is down)."""
    args = _make_args(tmp_path, n_scenes=1, scene_types="action_combat")
    stats: List[Dict] = generate_scene_chain(args, DEFAULT_CONFIG, args.nsfw_score)
    assert len(stats) == 1
    assert stats[0]["chars"] > 0
    assert stats[0]["status"] == "ok"
