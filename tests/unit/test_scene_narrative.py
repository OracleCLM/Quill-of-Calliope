"""Unit test per scripts/scene_narrative.py — generate_scene_chain, write_narrative_index, main."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.scene_narrative import generate_scene_chain, main, write_narrative_index


# ── write_narrative_index ─────────────────────────────────────────────────────

class TestWriteNarrativeIndex:
    def test_basic(self, tmp_path: Path) -> None:
        stats = [{"scene_num": 1, "scene_type": "action", "tier": "local",
                  "latency_ms": 100, "chars": 500, "status": "ok"}]
        write_narrative_index(tmp_path, stats, "my seed", "Yokai", "Alice,Bob", "2023-01-01T12:00:00")
        content = (tmp_path / "narrative_index.md").read_text(encoding="utf-8")
        assert "**Seed**: my seed" in content
        assert "**Location**: Yokai" in content
        assert "**Characters**: Alice,Bob" in content
        assert "| 1 | action | local | 100ms | 500 | ok |" in content
        assert "Scene 1" in content  # timeline

    def test_empty_stats(self, tmp_path: Path) -> None:
        write_narrative_index(tmp_path, [], "seed", "Loc", "", "2023-01-01")
        content = (tmp_path / "narrative_index.md").read_text(encoding="utf-8")
        assert "Avg: 0ms" in content

    def test_empty_char_list_writes_dash(self, tmp_path: Path) -> None:
        stats = [{"scene_num": 1, "scene_type": "a", "tier": "t",
                  "latency_ms": 0, "chars": 1, "status": "ok"}]
        write_narrative_index(tmp_path, stats, "seed", "Loc", "", "2023-01-01")
        content = (tmp_path / "narrative_index.md").read_text(encoding="utf-8")
        assert "**Characters**: —" in content

    def test_total_latency_sum(self, tmp_path: Path) -> None:
        stats = [
            {"scene_num": 1, "scene_type": "a", "tier": "t", "latency_ms": 200, "chars": 1, "status": "ok"},
            {"scene_num": 2, "scene_type": "b", "tier": "t", "latency_ms": 300, "chars": 1, "status": "ok"},
        ]
        write_narrative_index(tmp_path, stats, "s", "l", "c", "ts")
        content = (tmp_path / "narrative_index.md").read_text(encoding="utf-8")
        assert "Total latency: 500ms" in content
        assert "Avg: 250ms" in content


# ── generate_scene_chain ──────────────────────────────────────────────────────

def _args(tmp_path: Path, n_scenes: int = 1, scene_types: str = "action_combat",
          state_file: str | None = None) -> argparse.Namespace:
    return argparse.Namespace(
        seed="test seed",
        n_scenes=n_scenes,
        scene_types=scene_types,
        char_list="Alice,Bob",
        location="Kingdom of Yokai",
        output_dir=str(tmp_path),
        gateway_url="http://localhost:8766",
        state_file=state_file,
    )


class TestGenerateSceneChain:
    @patch("scripts.scene_narrative.route_scene")
    @patch("scripts.scene_narrative.dispatch_to_tier")
    def test_success_single_scene(self, mock_dispatch: MagicMock, mock_route: MagicMock,
                                   tmp_path: Path) -> None:
        mock_route.return_value = {"tier": "local", "provider": "ollama"}
        mock_dispatch.return_value = "Scene text content"
        stats = generate_scene_chain(_args(tmp_path), {}, {})
        assert len(stats) == 1
        assert stats[0]["scene_num"] == 1
        assert stats[0]["tier"] == "local"
        assert stats[0]["provider"] == "ollama"
        assert stats[0]["status"] == "ok"
        assert stats[0]["chars"] == len("Scene text content")
        assert (tmp_path / "scene_01_action_combat.md").exists()

    @patch("scripts.scene_narrative.route_scene")
    @patch("scripts.scene_narrative.dispatch_to_tier")
    def test_failure_sets_failed_status(self, mock_dispatch: MagicMock, mock_route: MagicMock,
                                        tmp_path: Path) -> None:
        mock_route.return_value = {"tier": "local", "provider": "ollama"}
        mock_dispatch.side_effect = Exception("Connection error")
        stats = generate_scene_chain(_args(tmp_path), {}, {})
        assert stats[0]["status"] == "failed"
        assert stats[0]["latency_ms"] == 0
        assert stats[0]["tier"] == "unknown"
        content = (tmp_path / "scene_01_action_combat.md").read_text(encoding="utf-8")
        assert "[Scene 1 generation failed]" in content

    @patch("scripts.scene_narrative.route_scene")
    @patch("scripts.scene_narrative.dispatch_to_tier")
    def test_cycling_scene_types(self, mock_dispatch: MagicMock, mock_route: MagicMock,
                                  tmp_path: Path) -> None:
        mock_route.return_value = {"tier": "local", "provider": "ollama"}
        mock_dispatch.return_value = "text"
        stats = generate_scene_chain(_args(tmp_path, n_scenes=2, scene_types="A,B"), {}, {})
        assert stats[0]["scene_type"] == "A"
        assert stats[1]["scene_type"] == "B"
        assert (tmp_path / "scene_01_A.md").exists()
        assert (tmp_path / "scene_02_B.md").exists()

    @patch("scripts.scene_narrative.route_scene")
    @patch("scripts.scene_narrative.dispatch_to_tier")
    def test_scene_type_slash_replaced(self, mock_dispatch: MagicMock, mock_route: MagicMock,
                                        tmp_path: Path) -> None:
        mock_route.return_value = {"tier": "local", "provider": "ollama"}
        mock_dispatch.return_value = "text"
        generate_scene_chain(_args(tmp_path, scene_types="a/b"), {}, {})
        assert (tmp_path / "scene_01_a_b.md").exists()

    @patch("scripts.scene_narrative.route_scene")
    @patch("scripts.scene_narrative.dispatch_to_tier")
    def test_continuation_uses_prev_scene(self, mock_dispatch: MagicMock, mock_route: MagicMock,
                                           tmp_path: Path) -> None:
        mock_route.return_value = {"tier": "local", "provider": "ollama"}
        mock_dispatch.side_effect = ["First scene text", "Second scene text"]
        stats = generate_scene_chain(_args(tmp_path, n_scenes=2, scene_types="S"), {}, {})
        assert len(stats) == 2
        assert all(s["status"] == "ok" for s in stats)

    @patch("scripts.scene_narrative.route_scene")
    @patch("scripts.scene_narrative.dispatch_to_tier")
    def test_state_file_branch(self, mock_dispatch: MagicMock, mock_route: MagicMock,
                                tmp_path: Path) -> None:
        mock_route.return_value = {"tier": "local", "provider": "ollama"}
        mock_dispatch.return_value = "Scene text"
        mock_ns = MagicMock()
        mock_ns_instance = MagicMock()
        mock_ns_instance.scene_count = 3
        mock_ns_instance.chars = ["Alice"]
        mock_ns_instance.to_prompt_context.return_value = "State context"
        mock_ns_instance.update_from_scene.return_value = {
            "chars_updated": 1, "location_changed": False, "threads_updated": 0,
        }
        mock_ns.NarrativeState.load.return_value = mock_ns_instance
        with patch.dict(sys.modules, {"narrative_state": mock_ns}):
            stats = generate_scene_chain(
                _args(tmp_path, state_file=str(tmp_path / "state.json")), {}, {},
            )
        assert stats[0]["status"] == "ok"
        mock_ns_instance.update_from_scene.assert_called_once()
        mock_ns_instance.save.assert_called_once()


# ── main() ────────────────────────────────────────────────────────────────────

class TestMain:
    @patch("scripts.scene_narrative.write_narrative_index")
    @patch("scripts.scene_narrative.generate_scene_chain")
    @patch("scripts.scene_narrative.load_config")
    def test_success(self, mock_cfg: MagicMock, mock_gen: MagicMock, mock_idx: MagicMock,
                     monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        mock_cfg.return_value = {}
        mock_gen.return_value = [{"scene_num": 1, "status": "ok"}]
        monkeypatch.setattr(sys, "argv", ["prog", "--seed", "test", "--output-dir", str(tmp_path)])
        main()
        mock_gen.assert_called_once()
        mock_idx.assert_called_once()

    @patch("scripts.scene_narrative.load_config")
    def test_invalid_nsfw_json_exits_1(self, mock_cfg: MagicMock,
                                        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(sys, "argv", [
            "prog", "--seed", "test", "--output-dir", str(tmp_path),
            "--nsfw-score", "{invalid}",
        ])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1

    @patch("scripts.scene_narrative.write_narrative_index")
    @patch("scripts.scene_narrative.generate_scene_chain")
    @patch("scripts.scene_narrative.load_config")
    def test_config_load_failure_uses_default(self, mock_cfg: MagicMock, mock_gen: MagicMock,
                                               mock_idx: MagicMock,
                                               monkeypatch: pytest.MonkeyPatch,
                                               tmp_path: Path) -> None:
        mock_cfg.side_effect = FileNotFoundError("not found")
        mock_gen.return_value = []
        monkeypatch.setattr(sys, "argv", ["prog", "--seed", "test", "--output-dir", str(tmp_path)])
        main()  # must not raise
        mock_gen.assert_called_once()
