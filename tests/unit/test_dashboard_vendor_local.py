"""Regression test: shell.html must not load JS from external CDN.

Privacy invariant 'local-only NO cloud upload': metadata browser (IP, UA)
must not leak to cubism.live2d.com or jsdelivr.net on page load.
Vendor JS files are checked into static/js/vendor/.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_TEMPLATE = Path(__file__).parents[2] / "app" / "calliope_shell" / "templates" / "shell.html"
_VENDOR_DIR = Path(__file__).parents[2] / "app" / "calliope_shell" / "static" / "js" / "vendor"


def test_template_loads_no_external_cdn():
    html = _TEMPLATE.read_text(encoding="utf-8")
    assert "cubism.live2d.com" not in html
    assert "cdn.jsdelivr.net" not in html


def test_template_references_vendor_local():
    html = _TEMPLATE.read_text(encoding="utf-8")
    assert "/static/js/vendor/live2dcubismcore.min.js" in html
    assert "/static/js/vendor/pixi.min.js" in html
    assert "/static/js/vendor/pixi-live2d-cubism4.min.js" in html


@pytest.mark.parametrize("filename,min_size_kb", [
    ("live2dcubismcore.min.js", 100),
    ("pixi.min.js", 200),
    ("pixi-live2d-cubism4.min.js", 50),
])
def test_vendor_file_exists_and_non_trivial(filename, min_size_kb):
    f = _VENDOR_DIR / filename
    assert f.exists(), f"vendored file missing: {filename}"
    assert f.stat().st_size > min_size_kb * 1024, f"{filename} suspiciously small (<{min_size_kb}KB)"
    head = f.read_bytes()[:200].decode("utf-8", errors="ignore")
    assert "<html" not in head.lower(), f"{filename} looks like HTML, not JS (failed download?)"
