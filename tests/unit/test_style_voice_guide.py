"""
Unit test per scripts/style_voice_guide.py.
load_samples e build_style_prefix — nessun ChromaDB, nessun filesystem reale.
"""
from __future__ import annotations

from unittest.mock import patch

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


# ─────────────────────────────────────────────────────────────────────────────
# Extended tests — _load_samples_from_chromadb, build_samples_file
# ─────────────────────────────────────────────────────────────────────────────

import sys  # noqa: E402

from scripts.style_voice_guide import _load_samples_from_chromadb, build_samples_file  # noqa: E402


# ── _load_samples_from_chromadb ───────────────────────────────────────────────

def test_load_from_chromadb_success():
    mock_col = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
    mock_col.get.return_value = {
        "documents": ["Doc1", "Doc2"],
        "metadatas": [
            {"author_type": "operator"},
            {"author_type": "char"},
        ],
    }
    mock_client = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
    mock_client.get_collection.return_value = mock_col
    mock_chromadb = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
    mock_chromadb.PersistentClient.return_value = mock_client
    with patch.dict(sys.modules, {"chromadb": mock_chromadb}):
        result = _load_samples_from_chromadb(n=5)
    assert "Doc1" in result
    assert "Doc2" not in result  # only operator


def test_load_from_chromadb_no_operator_falls_back_to_all():
    mock_col = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
    mock_col.get.return_value = {
        "documents": ["D1", "D2"],
        "metadatas": [{"author_type": "char"}, {"author_type": "char"}],
    }
    mock_client = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
    mock_client.get_collection.return_value = mock_col
    mock_chromadb = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
    mock_chromadb.PersistentClient.return_value = mock_client
    with patch.dict(sys.modules, {"chromadb": mock_chromadb}):
        result = _load_samples_from_chromadb(n=5)
    assert "D1" in result or "D2" in result  # fallback: all docs


def test_load_from_chromadb_exception_returns_empty():
    with patch.dict(sys.modules, {"chromadb": None}):
        result = _load_samples_from_chromadb(n=5)
    assert result == []


# ── build_samples_file ────────────────────────────────────────────────────────

def test_build_samples_file_uses_chromadb_samples(tmp_path):
    out = tmp_path / "voice.txt"
    with patch(f"{_SVG}._load_samples_from_chromadb", return_value=["Sample A", "Sample B"]):
        result_path = build_samples_file(output_path=out, n=2)
    assert result_path == out
    content = out.read_text(encoding="utf-8")
    assert "Sample A" in content
    assert "Sample B" in content


def test_build_samples_file_falls_back_to_stubs_on_empty(tmp_path):
    out = tmp_path / "voice.txt"
    with patch(f"{_SVG}._load_samples_from_chromadb", return_value=[]):
        build_samples_file(output_path=out, n=5)
    content = out.read_text(encoding="utf-8")
    for stub in _STUB_SAMPLES:
        assert stub in content


def test_build_samples_file_creates_parent_dirs(tmp_path):
    out = tmp_path / "a" / "b" / "voice.txt"
    with patch(f"{_SVG}._load_samples_from_chromadb", return_value=["X"]):
        build_samples_file(output_path=out)
    assert out.exists()
