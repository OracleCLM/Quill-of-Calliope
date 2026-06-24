"""Unit test per scripts/build_chromadb_index.py — chunk_text (pura)."""
from __future__ import annotations

from scripts.build_chromadb_index import chunk_text


def test_short_text():
    text = "short text"
    assert chunk_text(text) == [text]


def test_empty_string():
    assert chunk_text("") == [""]


def test_text_exactly_2000():
    text = "a" * 2000
    assert chunk_text(text) == [text]


def test_text_2001_triggers_chunking():
    text = "a" * 2001
    chunks = chunk_text(text)
    assert len(chunks) > 1


def test_chunk_boundaries():
    text = "a" * 2100
    chunks = chunk_text(text)
    assert len(chunks) == 5
    assert len(chunks[0]) == 512
    assert len(chunks[-1]) == 308


def test_overlap_correctness():
    text = "a" * 2100
    chunks = chunk_text(text)
    assert chunks[0][-64:] == chunks[1][:64]


def test_large_text_chunk_count():
    text = "a" * 10000
    chunks = chunk_text(text)
    assert len(chunks) == 23


def test_custom_chunk_size():
    text = "a" * 2100
    chunks = chunk_text(text, chunk_size=30, overlap=10)
    assert len(chunks) == 105
    assert len(chunks[0]) == 30


def test_custom_overlap():
    text = "a" * 2100
    chunks = chunk_text(text, chunk_size=30, overlap=5)
    assert len(chunks) == 84
    assert chunks[0][-5:] == chunks[1][:5]


def test_chunking_logic_exact_multiple():
    text = "a" * 2304
    chunks = chunk_text(text)
    assert len(chunks) == 5
    assert all(len(c) == 512 for c in chunks)
