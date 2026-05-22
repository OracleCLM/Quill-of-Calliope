"""Regression tests for P0 #2 — ChromaDB client connection leak.

Audit ref: docs/audit/CALLIOPE_DEEP_REVIEW_2026-05-22.md §2 P0 #2
Fix: @lru_cache(maxsize=1) on _chroma_client (server.py) and
_arc_chroma_client (plot_arc.py) → singleton per process.
"""
from __future__ import annotations

from app.calliope_shell import plot_arc, server


def test_server_chroma_client_is_singleton():
    server._chroma_client.cache_clear()
    c1 = server._chroma_client()
    c2 = server._chroma_client()
    assert c1 is c2


def test_arc_chroma_client_is_singleton():
    plot_arc._arc_chroma_client.cache_clear()
    c1 = plot_arc._arc_chroma_client()
    c2 = plot_arc._arc_chroma_client()
    assert c1 is c2


def test_server_chroma_client_has_cache_info():
    server._chroma_client.cache_clear()
    server._chroma_client()
    server._chroma_client()
    server._chroma_client()
    info = server._chroma_client.cache_info()
    assert info.hits == 2
    assert info.misses == 1
    assert info.currsize == 1


def test_arc_chroma_client_has_cache_info():
    plot_arc._arc_chroma_client.cache_clear()
    plot_arc._arc_chroma_client()
    plot_arc._arc_chroma_client()
    info = plot_arc._arc_chroma_client.cache_info()
    assert info.hits == 1
    assert info.misses == 1
    assert info.maxsize == 1
