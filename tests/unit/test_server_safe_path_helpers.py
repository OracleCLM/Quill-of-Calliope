"""GAP-68: test di sicurezza per _safe_variants_path e _safe_read_scene_file."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import app.calliope_shell.server as srv


# ═══════════════════════════════════════════════════════════════════
# _safe_variants_path
# ═══════════════════════════════════════════════════════════════════


def test_variants_empty_path_raises():
    with pytest.raises(ValueError, match="empty path"):
        srv._safe_variants_path("")


def test_variants_outside_allowed_roots_raises(tmp_path):
    bad = tmp_path / "calliope_x.variants.md"
    bad.touch()
    # tmp_path è fuori da /tmp standard se non è il tempdir di sistema
    import tempfile as _tf
    real_tmp = Path(_tf.gettempdir()).resolve()
    if not str(tmp_path.resolve()).startswith(str(real_tmp)):
        with pytest.raises(ValueError, match="outside allowed roots"):
            srv._safe_variants_path(str(bad))


def test_variants_wrong_filename_pattern_raises():
    import tempfile as _tf
    evil = Path(_tf.gettempdir()) / "calliope_x.wrongext.md"
    with pytest.raises(ValueError, match="filename pattern mismatch"):
        srv._safe_variants_path(str(evil))


def test_variants_traversal_raises():
    with pytest.raises(ValueError):
        srv._safe_variants_path("/etc/passwd")


def test_variants_valid_tmp_path_returns_path():
    import tempfile as _tf
    valid = Path(_tf.gettempdir()) / "calliope_abc123.variants.md"
    result = srv._safe_variants_path(str(valid))
    assert isinstance(result, Path)
    assert result.name == "calliope_abc123.variants.md"


# ═══════════════════════════════════════════════════════════════════
# _safe_read_scene_file
# ═══════════════════════════════════════════════════════════════════


def test_safe_read_empty_path_raises():
    with pytest.raises(ValueError, match="empty path"):
        srv._safe_read_scene_file("")


def test_safe_read_traversal_absolute_raises():
    with pytest.raises(ValueError, match="outside scenes directory"):
        srv._safe_read_scene_file("/etc/passwd")


def test_safe_read_dotdot_relative_raises(monkeypatch, tmp_path):
    scenes_dir = tmp_path / "scenes"
    scenes_dir.mkdir()
    monkeypatch.setattr(srv, "_SCENES_DIR", scenes_dir)
    with pytest.raises(ValueError, match="outside scenes directory"):
        srv._safe_read_scene_file("../../.env")


def test_safe_read_valid_relative_returns_content(monkeypatch, tmp_path):
    scenes_dir = tmp_path / "scenes"
    scenes_dir.mkdir()
    (scenes_dir / "scena1.md").write_text("Testo scena.", encoding="utf-8")
    monkeypatch.setattr(srv, "_SCENES_DIR", scenes_dir)
    content = srv._safe_read_scene_file("scena1.md")
    assert content == "Testo scena."


def test_safe_read_valid_absolute_returns_content(monkeypatch, tmp_path):
    scenes_dir = tmp_path / "scenes"
    scenes_dir.mkdir()
    scene_file = scenes_dir / "scena2.md"
    scene_file.write_text("Seconda scena.", encoding="utf-8")
    monkeypatch.setattr(srv, "_SCENES_DIR", scenes_dir)
    content = srv._safe_read_scene_file(str(scene_file))
    assert content == "Seconda scena."
