"""Regression tests for Sprint C1 — audit_trail SQLite schema + API.

Q5=write-only events, no reads. Q4 separate (privacy warning UI).
"""
from __future__ import annotations

import pytest

from app.calliope_shell import audit_trail


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    db = tmp_path / "test_audit.db"
    monkeypatch.setattr(audit_trail, "_DB_PATH", db)
    audit_trail.init_db()
    yield db


def test_event_kinds_constant_present():
    assert "char.create" in audit_trail.EVENT_KINDS
    assert "scene.refine" in audit_trail.EVENT_KINDS
    assert "llm_routing.switch" in audit_trail.EVENT_KINDS


def test_highlight_subset_of_all():
    assert audit_trail.HIGHLIGHT_KINDS.issubset(audit_trail.EVENT_KINDS)


def test_no_read_kinds_in_event_kinds():
    """Q5 livello (b): solo write events, no read/browse."""
    forbidden = ("read", "browse", "view", "fetch", "list", "search")
    for kind in audit_trail.EVENT_KINDS:
        for f in forbidden:
            assert f not in kind, f"read-like kind found: {kind}"


def test_init_db_idempotent(fresh_db):
    audit_trail.init_db()
    audit_trail.init_db()


def test_log_event_persists(fresh_db):
    audit_trail.log_event("char.create", subject="Aurora", detail="new char")
    events = audit_trail.recent_events(limit=5, mode="verbose")
    assert len(events) == 1
    assert events[0]["kind"] == "char.create"
    assert events[0]["subject"] == "Aurora"
    assert events[0]["detail"] == "new char"


def test_log_event_rejects_unknown_kind(fresh_db):
    audit_trail.log_event("evil.kind", subject="x")
    events = audit_trail.recent_events(limit=5, mode="verbose")
    assert len(events) == 0


def test_recent_events_highlight_mode_filters(fresh_db):
    audit_trail.log_event("char.create", subject="Aurora")  # highlight
    audit_trail.log_event("char.fact_append", subject="Aurora")  # not highlight
    audit_trail.log_event("scene.refine", subject="scene01")  # highlight
    highlight = audit_trail.recent_events(limit=10, mode="highlight")
    verbose = audit_trail.recent_events(limit=10, mode="verbose")
    assert len(highlight) == 2
    assert len(verbose) == 3
    kinds = {e["kind"] for e in highlight}
    assert "char.fact_append" not in kinds


def test_recent_events_ordering_by_ts_desc(fresh_db):
    audit_trail.log_event("char.create", subject="first")
    audit_trail.log_event("char.create", subject="second")
    audit_trail.log_event("char.create", subject="third")
    events = audit_trail.recent_events(limit=10, mode="verbose")
    subjects = [e["subject"] for e in events]
    assert subjects == ["third", "second", "first"]


def test_metadata_json_persists(fresh_db):
    audit_trail.log_event(
        "scene.blend",
        subject="scene01",
        metadata={"variants": [1, 2], "latency_ms": 1234},
    )
    events = audit_trail.recent_events(limit=1, mode="verbose")
    import json
    meta = json.loads(events[0]["metadata_json"])
    assert meta["variants"] == [1, 2]
    assert meta["latency_ms"] == 1234


def test_recent_events_kinds_filter_overrides_mode(fresh_db):
    audit_trail.log_event("char.create", subject="A")
    audit_trail.log_event("scene.refine", subject="S")
    audit_trail.log_event("translate.run", subject="T")
    only_translate = audit_trail.recent_events(
        limit=10, kinds_filter=["translate.run"]
    )
    assert len(only_translate) == 1
    assert only_translate[0]["kind"] == "translate.run"


def test_recent_events_empty_filter_returns_empty(fresh_db):
    audit_trail.log_event("char.create", subject="A")
    result = audit_trail.recent_events(limit=10, kinds_filter=[])
    assert result == []


def test_log_event_no_exception_on_db_failure(fresh_db, monkeypatch):
    """Audit must never break the operation it observes."""
    def boom(*_a, **_k):
        raise RuntimeError("simulated DB failure")
    monkeypatch.setattr(audit_trail, "_conn", boom)
    # Must not raise
    audit_trail.log_event("char.create", subject="x")


def test_recent_events_db_error_returns_empty(fresh_db, monkeypatch):
    monkeypatch.setattr(audit_trail, "_DB_PATH", fresh_db / "nonexistent_dir" / "bad.db")
    result = audit_trail.recent_events(limit=5)
    assert result == []


def test_init_db_exception_doesnt_propagate(tmp_path, monkeypatch):
    from unittest.mock import patch
    monkeypatch.setattr(audit_trail, "_DB_PATH", tmp_path / "bad.db")
    with patch("app.calliope_shell.audit_trail._conn", side_effect=RuntimeError("disk full")):
        audit_trail.init_db()
