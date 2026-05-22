"""Regression tests for P0 #1 — path traversal on /api/scene/* endpoints.

Audit ref: docs/audit/CALLIOPE_DEEP_REVIEW_2026-05-22.md §2 P0 #1
Fix: _safe_read_scene_file restricts reads to _SCENES_DIR.
"""
from __future__ import annotations

import pytest

from app.calliope_shell.server import _SCENES_DIR, _safe_read_scene_file


def test_safe_read_rejects_relative_traversal():
    with pytest.raises(ValueError, match="outside scenes directory"):
        _safe_read_scene_file("../../../../etc/passwd")


def test_safe_read_rejects_absolute_outside_scenes():
    with pytest.raises(ValueError, match="outside scenes directory"):
        _safe_read_scene_file("/etc/passwd")


def test_safe_read_rejects_dotdot_segments_in_relative():
    with pytest.raises(ValueError, match="outside scenes directory"):
        _safe_read_scene_file("subdir/../../../../etc/hosts")


def test_safe_read_rejects_empty_path():
    with pytest.raises(ValueError, match="empty path"):
        _safe_read_scene_file("")


def test_safe_read_accepts_path_inside_scenes(tmp_path, monkeypatch):
    fake_scenes = tmp_path / "scenes"
    fake_scenes.mkdir()
    scene_file = fake_scenes / "scene01.md"
    scene_file.write_text("Once upon a time.", encoding="utf-8")

    monkeypatch.setattr("app.calliope_shell.server._SCENES_DIR", fake_scenes)

    result = _safe_read_scene_file("scene01.md")
    assert result == "Once upon a time."


def test_safe_read_accepts_absolute_inside_scenes(tmp_path, monkeypatch):
    fake_scenes = tmp_path / "scenes"
    fake_scenes.mkdir()
    scene_file = fake_scenes / "scene_abs.md"
    scene_file.write_text("Absolute happy path.", encoding="utf-8")

    monkeypatch.setattr("app.calliope_shell.server._SCENES_DIR", fake_scenes)

    result = _safe_read_scene_file(str(scene_file))
    assert result == "Absolute happy path."


def test_scenes_dir_resolves_to_repo_scenes():
    assert _SCENES_DIR.name == "scenes"
    assert _SCENES_DIR.parent.name == "Quill_of_Calliope"
