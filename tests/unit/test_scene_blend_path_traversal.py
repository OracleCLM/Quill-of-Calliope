"""Regression tests for P1 #4 — path traversal on /api/scene/blend.

Same vector as P0 #1 (audit 2026-05-22) but on a different endpoint.
Fix: _safe_variants_path() restricts reads to tmp dir + scenes/ + filename
pattern match (calliope_*.variants.md).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.calliope_shell.server import _safe_variants_path


def test_blend_rejects_relative_traversal():
    with pytest.raises(ValueError, match="outside allowed roots"):
        _safe_variants_path("../../../../etc/passwd")


def test_blend_rejects_absolute_outside():
    with pytest.raises(ValueError, match="outside allowed roots"):
        _safe_variants_path("/etc/passwd")


def test_blend_rejects_empty_path():
    with pytest.raises(ValueError, match="empty path"):
        _safe_variants_path("")


def test_blend_rejects_wrong_filename_pattern():
    """Even inside /tmp, only calliope_*.variants.md filenames allowed."""
    with tempfile.NamedTemporaryFile(suffix=".sh", prefix="evil_", delete=False) as f:
        path = f.name
    try:
        with pytest.raises(ValueError, match="filename pattern mismatch"):
            _safe_variants_path(path)
    finally:
        Path(path).unlink(missing_ok=True)


def test_blend_accepts_legit_tmp_variants_file():
    with tempfile.NamedTemporaryFile(suffix=".variants.md", prefix="calliope_", delete=False) as f:
        path = f.name
    try:
        result = _safe_variants_path(path)
        assert result == Path(path).resolve()
    finally:
        Path(path).unlink(missing_ok=True)


def test_blend_rejects_relative_dotdot_pointing_to_tmp_via_legit_prefix():
    """Even if attacker chains /tmp/legit/../etc/passwd, resolve() catches it."""
    with pytest.raises(ValueError, match="outside allowed roots|filename pattern"):
        _safe_variants_path("/tmp/calliope_xxx.variants.md/../../../../etc/passwd")
