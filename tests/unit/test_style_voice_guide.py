"""
Unit test per scripts/style_voice_guide.py.
load_samples e build_style_prefix — nessun ChromaDB, nessun filesystem reale.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.style_voice_guide import (
    _STUB_SAMPLES,
    build_style_prefix,
    load_samples,
)

_SVG = "scripts.style_voice_guide"


# ── load_samples ──────────────────────────────────────────────────────────────

def test_load_samples_missing_file_returns_stubs(tmp_path):
    missing = tmp_path / "nonexistent.txt"
    result = load_samples(path=missing, k=2)
    assert result == _STUB_SAMPLES[:2]


def test_load_samples_missing_file_k_capped(tmp_path):
    missing = tmp_path / "nonexistent.txt"
    result = load_samples(path=missing, k=100)
    assert result == _STUB_SAMPLES  # :k falls back to full list when k > len(stubs)


def test_load_samples_from_file(tmp_path):
    f = tmp_path / "samples.txt"
    f.write_text("Campione uno---Campione due---Campione tre", encoding="utf-8")
    result = load_samples(path=f, k=2)
    assert len(result) == 2
    for s in result:
        assert s in ["Campione uno", "Campione due", "Campione tre"]


def test_load_samples_k_greater_than_file_entries(tmp_path):
    f = tmp_path / "samples.txt"
    f.write_text("Solo---questo", encoding="utf-8")
    result = load_samples(path=f, k=10)
    assert len(result) == 2  # min(10, 2)


def test_load_samples_k1_returns_one(tmp_path):
    f = tmp_path / "samples.txt"
    f.write_text("A---B---C---D", encoding="utf-8")
    result = load_samples(path=f, k=1)
    assert len(result) == 1


# ── build_style_prefix ────────────────────────────────────────────────────────

def test_build_style_prefix_contains_header():
    prefix = build_style_prefix(k=2)
    assert "Write in this style" in prefix


def test_build_style_prefix_injects_samples():
    with patch(f"{_SVG}.load_samples", return_value=["Sample A", "Sample B"]) as mock_load:
        prefix = build_style_prefix(k=2)
        mock_load.assert_called_once_with(k=2)
    assert "Sample A" in prefix
    assert "Sample B" in prefix


def test_build_style_prefix_example_passages_label():
    with patch(f"{_SVG}.load_samples", return_value=["X"]):
        prefix = build_style_prefix(k=1)
    assert "Example passages" in prefix
