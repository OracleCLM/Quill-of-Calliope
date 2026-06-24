"""Unit test per scripts/generate_scene_samples.py — save_scene_md (pura)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from scripts.generate_scene_samples import save_scene_md

_DT = "scripts.generate_scene_samples.datetime"
_FIXED_ISO = "2026-06-24T12:00:00"


def _dt_mock():
    m = MagicMock()
    m.utcnow.return_value = MagicMock(isoformat=lambda: _FIXED_ISO)
    return m


def test_path_name_format(tmp_path):
    with patch(_DT, _dt_mock()):
        result = save_scene_md(5, "forest_encounter", "high", "seed", "text", 1.0, tmp_path)
    assert result.name == "sample_05_forest_encounter.md"


def test_file_exists(tmp_path):
    with patch(_DT, _dt_mock()):
        result = save_scene_md(5, "forest_encounter", "high", "seed", "text", 1.0, tmp_path)
    assert result.exists()


def test_frontmatter_contains_scene_num(tmp_path):
    with patch(_DT, _dt_mock()):
        save_scene_md(5, "forest_encounter", "high", "seed", "text", 1.0, tmp_path)
    content = (tmp_path / "sample_05_forest_encounter.md").read_text()
    assert "scene_num: 05" in content


def test_frontmatter_latency_two_decimals(tmp_path):
    with patch(_DT, _dt_mock()):
        save_scene_md(5, "forest_encounter", "high", "seed", "text", 1.2345, tmp_path)
    content = (tmp_path / "sample_05_forest_encounter.md").read_text()
    assert "latency_sec: 1.23" in content


def test_body_heading_titlecased(tmp_path):
    with patch(_DT, _dt_mock()):
        save_scene_md(5, "forest_encounter", "high", "seed", "text", 1.0, tmp_path)
    content = (tmp_path / "sample_05_forest_encounter.md").read_text()
    assert "# Scene 05 — Forest Encounter" in content


def test_body_contains_text(tmp_path):
    with patch(_DT, _dt_mock()):
        save_scene_md(5, "forest_encounter", "high", "seed", "The quick brown fox.", 1.0, tmp_path)
    content = (tmp_path / "sample_05_forest_encounter.md").read_text()
    assert "The quick brown fox." in content


def test_seed_truncated_at_80_chars(tmp_path):
    long_seed = "a" * 100
    with patch(_DT, _dt_mock()):
        save_scene_md(5, "forest_encounter", "high", long_seed, "text", 1.0, tmp_path)
    content = (tmp_path / "sample_05_forest_encounter.md").read_text()
    assert 'seed: "' + "a" * 80 + '"' in content
    assert "a" * 100 not in content


def test_num_zero_padded(tmp_path):
    with patch(_DT, _dt_mock()):
        save_scene_md(3, "action_combat", "tier", "s", "t", 0.5, tmp_path)
    content = (tmp_path / "sample_03_action_combat.md").read_text()
    assert "scene_num: 03" in content
    assert "# Scene 03" in content
