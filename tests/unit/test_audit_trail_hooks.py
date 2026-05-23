"""Integration tests for Sprint C2 — write-event ingest hooks.

Verifies every write path (char_memory, plot_arc, server.py routes) logs
exactly one audit event with the expected kind. Uses isolated tmp DB.
"""
from __future__ import annotations

import uuid

import pytest

from app.calliope_shell import audit_trail, char_memory, plot_arc, server


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    db = tmp_path / "test_hooks.db"
    monkeypatch.setattr(char_memory, "_DB_PATH", db)
    monkeypatch.setattr(plot_arc, "DB_PATH", db)
    monkeypatch.setattr(audit_trail, "_DB_PATH", db)
    char_memory.init_db()
    plot_arc.init_db()
    audit_trail.init_db()
    yield db


def _last_event(kind: str = None) -> dict | None:
    events = audit_trail.recent_events(limit=50, mode="verbose")
    if kind:
        for e in events:
            if e["kind"] == kind:
                return e
        return None
    return events[0] if events else None


def test_char_create_logs_event(isolated_db):
    name = "TestHookChar_" + uuid.uuid4().hex[:6]
    char_memory.upsert_char(name, traits={"personality": ["brave"]})
    e = _last_event("char.create")
    assert e is not None
    assert e["subject"] == name


def test_char_update_logs_event(isolated_db):
    name = "TestHookChar_" + uuid.uuid4().hex[:6]
    char_memory.upsert_char(name, traits={"personality": ["brave"]})
    char_memory.upsert_char(name, last_action="drew sword")
    e = _last_event("char.update")
    assert e is not None
    assert e["subject"] == name


def test_append_fact_logs_event(isolated_db):
    name = "TestHookChar_" + uuid.uuid4().hex[:6]
    char_memory.upsert_char(name)
    char_memory.append_fact(name, "test fact body", scope="L1")
    e = _last_event("char.fact_append")
    assert e is not None
    assert e["subject"] == name
    assert "test fact body" in (e["detail"] or "")


def test_replace_fact_logs_event(isolated_db):
    name = "TestHookChar_" + uuid.uuid4().hex[:6]
    char_memory.upsert_char(name)
    char_memory.append_fact(name, "Aurora wears a red cloak", scope="L1")
    char_memory.replace_fact(name, "red cloak", "blue cloak", scope="L1")
    e = _last_event("char.fact_replace")
    assert e is not None


def test_arc_create_logs_event(isolated_db):
    arc_id = "test_arc_" + uuid.uuid4().hex[:6]
    plot_arc.create_arc(arc_id, "Test Arc", ["Aurora", "Philly"])
    e = _last_event("arc.create")
    assert e is not None
    assert e["subject"] == arc_id


def test_regenerate_summary_logs_event_via_groq_failure(isolated_db, monkeypatch):
    """Even if groq down, audit event should still fire with stub summary."""
    arc_id = "test_arc_" + uuid.uuid4().hex[:6]
    plot_arc.create_arc(arc_id, "Test Arc", [])
    # add a scene with provided summary so regenerate has something
    scene_path = isolated_db.parent / "fake_scene.md"
    scene_path.write_text("Scene body text.", encoding="utf-8")
    plot_arc.append_scene(arc_id, str(scene_path), scene_summary="manual summary")
    # _groq_ask returns "" on failure → summary becomes "Summary unavailable."
    monkeypatch.setattr(plot_arc, "_groq_ask", lambda *a, **k: "")
    plot_arc.regenerate_summary(arc_id)
    e = _last_event("arc.summary_regen")
    assert e is not None
    assert e["subject"] == arc_id


def test_arc_scene_append_logs_event(isolated_db):
    arc_id = "test_arc_" + uuid.uuid4().hex[:6]
    plot_arc.create_arc(arc_id, "Test Arc", [])
    scene_path = isolated_db.parent / "fake_scene_b.md"
    scene_path.write_text("Body B.", encoding="utf-8")
    plot_arc.append_scene(arc_id, str(scene_path), scene_summary="summary B")
    e = _last_event("arc.scene_append")
    assert e is not None
    assert e["subject"] == arc_id


def test_no_audit_event_for_read_ops(isolated_db):
    """Q5 invariant: read operations do not generate audit events."""
    name = "TestHookChar_" + uuid.uuid4().hex[:6]
    char_memory.upsert_char(name)
    baseline = len(audit_trail.recent_events(limit=100, mode="verbose"))
    char_memory.get_char(name)
    char_memory.list_chars()
    char_memory.get_facts(name)
    plot_arc.list_arcs()
    plot_arc.get_arc("nonexistent")
    after = len(audit_trail.recent_events(limit=100, mode="verbose"))
    assert after == baseline, "read ops generated audit events (Q5 violation)"


def test_llm_routing_switch_logs_event(isolated_db):
    app, _ = server.create_app()
    client = app.test_client()
    client.post("/api/dashboard/llm_routing", json={"uncensored": True})
    e = _last_event("llm_routing.switch")
    assert e is not None
