"""Regression tests for P1 #12 — ChromaDB upsert non-incremental.

Audit ref: docs/audit/CALLIOPE_DEEP_REVIEW_2026-05-22.md §2 P1 #12
Fix: track per-arc fingerprint (updated_at + summary length) and only
upsert rows whose fingerprint changed since last call.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.calliope_shell import plot_arc


@pytest.fixture(autouse=True)
def _reset_cache():
    plot_arc._arc_upsert_cache.clear()
    yield
    plot_arc._arc_upsert_cache.clear()


def test_fingerprint_changes_with_updated_at():
    fp1 = plot_arc._arc_fingerprint({"updated_at": "2026-01-01", "summary": "x"})
    fp2 = plot_arc._arc_fingerprint({"updated_at": "2026-02-01", "summary": "x"})
    assert fp1 != fp2


def test_fingerprint_changes_with_summary_length():
    fp1 = plot_arc._arc_fingerprint({"updated_at": "t", "summary": "short"})
    fp2 = plot_arc._arc_fingerprint({"updated_at": "t", "summary": "much longer text"})
    assert fp1 != fp2


def test_fingerprint_stable_for_unchanged_arc():
    arc = {"updated_at": "t", "summary": "abc", "arc_id": "x"}
    assert plot_arc._arc_fingerprint(arc) == plot_arc._arc_fingerprint(arc)


def test_search_only_upserts_changed_arcs():
    fake_col = MagicMock()
    fake_col.query.return_value = {"ids": [[]], "documents": [[]]}
    fake_client = MagicMock()
    fake_client.get_or_create_collection.return_value = fake_col

    arcs_v1 = [
        {"arc_id": "a1", "title": "Arc 1", "summary": "first summary", "updated_at": "2026-01-01"},
        {"arc_id": "a2", "title": "Arc 2", "summary": "second summary", "updated_at": "2026-01-01"},
    ]
    with patch.object(plot_arc, "_arc_chroma_client", return_value=fake_client), \
         patch.object(plot_arc, "list_arcs", return_value=arcs_v1):
        plot_arc.search_arcs_by_topic("query")

    first_call = fake_col.upsert.call_args
    assert set(first_call.kwargs["ids"]) == {"a1", "a2"}

    fake_col.reset_mock()
    fake_col.query.return_value = {"ids": [[]], "documents": [[]]}

    with patch.object(plot_arc, "_arc_chroma_client", return_value=fake_client), \
         patch.object(plot_arc, "list_arcs", return_value=arcs_v1):
        plot_arc.search_arcs_by_topic("query")

    fake_col.upsert.assert_not_called()


def test_search_upserts_only_modified_arc():
    fake_col = MagicMock()
    fake_col.query.return_value = {"ids": [[]], "documents": [[]]}
    fake_client = MagicMock()
    fake_client.get_or_create_collection.return_value = fake_col

    arcs_v1 = [
        {"arc_id": "a1", "title": "Arc 1", "summary": "first", "updated_at": "2026-01-01"},
        {"arc_id": "a2", "title": "Arc 2", "summary": "second", "updated_at": "2026-01-01"},
    ]
    with patch.object(plot_arc, "_arc_chroma_client", return_value=fake_client), \
         patch.object(plot_arc, "list_arcs", return_value=arcs_v1):
        plot_arc.search_arcs_by_topic("q")

    # Mutate only a2
    arcs_v2 = [
        {"arc_id": "a1", "title": "Arc 1", "summary": "first", "updated_at": "2026-01-01"},
        {"arc_id": "a2", "title": "Arc 2", "summary": "MUCH LONGER SECOND SUMMARY HERE", "updated_at": "2026-02-01"},
    ]
    fake_col.reset_mock()
    fake_col.query.return_value = {"ids": [[]], "documents": [[]]}

    with patch.object(plot_arc, "_arc_chroma_client", return_value=fake_client), \
         patch.object(plot_arc, "list_arcs", return_value=arcs_v2):
        plot_arc.search_arcs_by_topic("q")

    call = fake_col.upsert.call_args
    assert call.kwargs["ids"] == ["a2"], f"expected only a2 upserted, got {call.kwargs['ids']}"


def test_search_empty_arcs_no_upsert():
    fake_col = MagicMock()
    fake_col.query.return_value = {"ids": [[]], "documents": [[]]}
    fake_client = MagicMock()
    fake_client.get_or_create_collection.return_value = fake_col

    with patch.object(plot_arc, "_arc_chroma_client", return_value=fake_client), \
         patch.object(plot_arc, "list_arcs", return_value=[]):
        result = plot_arc.search_arcs_by_topic("q")

    fake_col.upsert.assert_not_called()
    assert result == []
