"""GAP-61: test per regenerate_summary e _arc_fingerprint in plot_arc."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

import app.calliope_shell.plot_arc as pa


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path):
    db = tmp_path / "arc_regen.db"
    monkeypatch.setattr(pa, "DB_PATH", db)
    monkeypatch.setattr("app.calliope_shell.plot_arc.audit_trail", MagicMock(), raising=False)
    pa.init_db()
    yield


# ── regenerate_summary ────────────────────────────────────────────────────────


def test_regenerate_missing_arc_returns_empty(monkeypatch):
    monkeypatch.setattr(pa, "_groq_ask", lambda *a, **kw: "irrelevant")
    result = pa.regenerate_summary("arc-not-exists")
    assert result == ""


def test_regenerate_arc_without_scenes_returns_empty(monkeypatch):
    pa.create_arc("regen-arc", "Test Arc", [])
    monkeypatch.setattr(pa, "_groq_ask", lambda *a, **kw: "should not be called")
    result = pa.regenerate_summary("regen-arc")
    assert result == ""


def _insert_scene(arc_id, scene_id, summary, order):
    with pa._lock, pa._conn() as c:
        c.execute(
            "INSERT INTO plot_arc_scenes (arc_id, scene_order, scene_id, scene_md_path, scene_summary) "
            "VALUES (?, ?, ?, ?, ?)",
            (arc_id, order, scene_id, "", summary),
        )


def test_regenerate_returns_groq_output(monkeypatch):
    pa.create_arc("regen-a2", "Arc with scenes", [])
    _insert_scene("regen-a2", "sc-1", "Aurora defeats the dragon.", 0)
    monkeypatch.setattr(pa, "_groq_ask", lambda *a, **kw: "Arc summary generated.")
    result = pa.regenerate_summary("regen-a2")
    assert result == "Arc summary generated."


def test_regenerate_updates_db(monkeypatch):
    pa.create_arc("regen-a3", "Arc updates", [])
    _insert_scene("regen-a3", "sc-2", "The village burns.", 0)
    monkeypatch.setattr(pa, "_groq_ask", lambda *a, **kw: "Updated summary text.")
    pa.regenerate_summary("regen-a3")
    arc = pa.get_arc("regen-a3")
    assert arc["summary"] == "Updated summary text."


def test_regenerate_empty_groq_uses_default(monkeypatch):
    pa.create_arc("regen-a4", "Arc groq empty", [])
    _insert_scene("regen-a4", "sc-3", "Short summary.", 0)
    monkeypatch.setattr(pa, "_groq_ask", lambda *a, **kw: "")
    result = pa.regenerate_summary("regen-a4")
    assert result == "Summary unavailable."


def test_regenerate_groq_receives_joined_summaries(monkeypatch):
    pa.create_arc("regen-a5", "Arc multi-scene", [])
    _insert_scene("regen-a5", "sc-4", "Scene one summary.", 0)
    _insert_scene("regen-a5", "sc-5", "Scene two summary.", 1)

    received_prompt = []

    def mock_groq(prompt, **kw):
        received_prompt.append(prompt)
        return "Combined."

    monkeypatch.setattr(pa, "_groq_ask", mock_groq)
    pa.regenerate_summary("regen-a5")
    assert len(received_prompt) == 1
    assert "Scene one summary" in received_prompt[0]
    assert "Scene two summary" in received_prompt[0]


# ── _arc_fingerprint ──────────────────────────────────────────────────────────


def test_arc_fingerprint_includes_updated_at():
    arc = {"arc_id": "a", "updated_at": "2024-01-01", "summary": "short", "title": "T"}
    fp = pa._arc_fingerprint(arc)
    assert "2024-01-01" in fp


def test_arc_fingerprint_includes_summary_length():
    summary = "a" * 42
    arc = {"arc_id": "a", "updated_at": "", "summary": summary, "title": "T"}
    fp = pa._arc_fingerprint(arc)
    assert "42" in fp


def test_arc_fingerprint_no_summary_uses_title():
    arc = {"arc_id": "a", "updated_at": "", "title": "AB"}
    fp = pa._arc_fingerprint(arc)
    assert "2" in fp  # len("AB") == 2


def test_arc_fingerprint_missing_fields_no_crash():
    fp = pa._arc_fingerprint({})
    assert isinstance(fp, str)


def test_arc_fingerprint_changes_when_summary_changes():
    arc1 = {"arc_id": "a", "updated_at": "t", "summary": "short"}
    arc2 = {"arc_id": "a", "updated_at": "t", "summary": "much longer summary here"}
    assert pa._arc_fingerprint(arc1) != pa._arc_fingerprint(arc2)
