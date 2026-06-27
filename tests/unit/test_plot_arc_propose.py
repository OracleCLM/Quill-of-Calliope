"""GAP-57: test per propose_next_scene — parsing LLM output + fallback."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

import app.calliope_shell.plot_arc as pa


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path):
    db = tmp_path / "arc_propose.db"
    monkeypatch.setattr(pa, "DB_PATH", db)
    monkeypatch.setattr("app.calliope_shell.plot_arc.audit_trail", MagicMock(), raising=False)
    pa.init_db()
    yield


# ── arc inesistente ───────────────────────────────────────────────────────────


def test_propose_missing_arc_returns_empty_dict(monkeypatch):
    monkeypatch.setattr(pa, "_groq_ask", lambda *a, **kw: "")
    result = pa.propose_next_scene("arc-inesistente")
    assert result == {}


# ── parsing output LLM ────────────────────────────────────────────────────────


def test_propose_parses_scene_type(monkeypatch):
    pa.create_arc("p-arc", "Test Arc", [])
    monkeypatch.setattr(pa, "_groq_ask", lambda *a, **kw: (
        "scene_type: dialogue\nprompt: Two characters debate the plan."
    ))
    result = pa.propose_next_scene("p-arc")
    assert result["scene_type"] == "dialogue"


def test_propose_parses_prompt_seed(monkeypatch):
    pa.create_arc("p2-arc", "Test Arc", [])
    monkeypatch.setattr(pa, "_groq_ask", lambda *a, **kw: (
        "scene_type: dialogue\nprompt: Aurora and Mao argue."
    ))
    result = pa.propose_next_scene("p2-arc")
    assert "Aurora" in result["prompt_seed"]


def test_propose_invalid_scene_type_uses_default(monkeypatch):
    pa.create_arc("p3-arc", "Test Arc", [])
    monkeypatch.setattr(pa, "_groq_ask", lambda *a, **kw: (
        "scene_type: invalid_type\nprompt: Something happens."
    ))
    result = pa.propose_next_scene("p3-arc")
    assert result["scene_type"] == "mystery_investigation"


def test_propose_valid_scene_types(monkeypatch):
    valid_types = [
        "action_combat", "mystery_investigation", "dialogue",
        "exploration", "confrontation", "tragedy", "celebration",
    ]
    for stype in valid_types:
        pa.create_arc(f"p4-{stype}", "T", [])
        monkeypatch.setattr(pa, "_groq_ask", lambda *a, t=stype, **kw: (
            f"scene_type: {t}\nprompt: Next scene."
        ))
        result = pa.propose_next_scene(f"p4-{stype}")
        assert result["scene_type"] == stype


def test_propose_no_prompt_line_uses_content_fallback(monkeypatch):
    pa.create_arc("p5-arc", "Test Arc", [])
    monkeypatch.setattr(pa, "_groq_ask", lambda *a, **kw: "Raw groq output fallback.")
    result = pa.propose_next_scene("p5-arc")
    assert "Raw groq output fallback" in result["prompt_seed"]


def test_propose_empty_groq_uses_default_prompt(monkeypatch):
    pa.create_arc("p6-arc", "Test Arc", [])
    monkeypatch.setattr(pa, "_groq_ask", lambda *a, **kw: "")
    result = pa.propose_next_scene("p6-arc")
    assert result["prompt_seed"]  # non vuoto (default)
    assert "Continue" in result["prompt_seed"]


def test_propose_returns_hint_used(monkeypatch):
    pa.create_arc("p7-arc", "Test Arc", [])
    monkeypatch.setattr(pa, "_groq_ask", lambda *a, **kw: "scene_type: dialogue\nprompt: X.")
    result = pa.propose_next_scene("p7-arc", hint="Show the betrayal")
    assert result["hint_used"] == "Show the betrayal"


def test_propose_hint_none_propagated(monkeypatch):
    pa.create_arc("p8-arc", "Test Arc", [])
    monkeypatch.setattr(pa, "_groq_ask", lambda *a, **kw: "scene_type: dialogue\nprompt: X.")
    result = pa.propose_next_scene("p8-arc")
    assert result["hint_used"] is None


def test_propose_result_has_required_keys(monkeypatch):
    pa.create_arc("p9-arc", "Test Arc", [])
    monkeypatch.setattr(pa, "_groq_ask", lambda *a, **kw: "scene_type: dialogue\nprompt: X.")
    result = pa.propose_next_scene("p9-arc")
    assert "scene_type" in result
    assert "prompt_seed" in result
    assert "hint_used" in result
