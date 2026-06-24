"""Unit test per le funzioni SQLite core di app/calliope_shell/plot_arc.py."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.calliope_shell import plot_arc

_GROQ = "app.calliope_shell.plot_arc._groq_ask"


@pytest.fixture
def db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_plot_arc.db"
    monkeypatch.setattr(plot_arc, "DB_PATH", db_path)
    plot_arc.init_db()
    yield tmp_path


def _scene_file(tmp_path, name="scene1.md"):
    p = tmp_path / name
    p.write_text("A dark battle erupted in the forest clearing.")
    return str(p)


# ── create_arc / get_arc ──────────────────────────────────────────────────────

def test_create_arc_returns_dict(db):
    result = plot_arc.create_arc("a1", "Titolo", ["Alice"])
    assert isinstance(result, dict)
    assert "arc_id" in result
    assert "title" in result


def test_create_arc_get_arc(db):
    plot_arc.create_arc("a1", "Titolo", ["Alice"])
    result = plot_arc.get_arc("a1")
    assert result is not None
    assert result["arc_id"] == "a1"


def test_get_arc_not_found(db):
    assert plot_arc.get_arc("nonexistent") is None


def test_create_arc_chars_stored(db):
    plot_arc.create_arc("a1", "Titolo", ["Alice", "Bob"])
    result = plot_arc.get_arc("a1")
    assert result["chars"] == ["Alice", "Bob"]


def test_create_arc_idempotent(db):
    plot_arc.create_arc("a1", "Titolo", ["Alice"])
    plot_arc.create_arc("a1", "Titolo Aggiornato", ["Alice"])
    assert len(plot_arc.list_arcs()) == 1


def test_arc_has_scenes_key(db):
    plot_arc.create_arc("a1", "Titolo", ["Alice"])
    result = plot_arc.get_arc("a1")
    assert "scenes" in result


# ── list_arcs ─────────────────────────────────────────────────────────────────

def test_list_arcs_empty(db):
    assert plot_arc.list_arcs() == []


def test_list_arcs_after_create(db):
    plot_arc.create_arc("a1", "Titolo 1", ["Alice"])
    plot_arc.create_arc("a2", "Titolo 2", ["Bob"])
    assert len(plot_arc.list_arcs()) == 2


def test_list_arcs_status_filter(db):
    plot_arc.create_arc("a1", "Active Arc", ["Alice"])
    conn = plot_arc._conn()
    conn.execute(
        "INSERT INTO plot_arcs (arc_id, title, chars, status) VALUES (?, ?, ?, ?)",
        ("a2", "Archived Arc", '["Bob"]', "archived"),
    )
    conn.commit()
    conn.close()
    result = plot_arc.list_arcs(status="archived")
    assert len(result) == 1
    assert result[0]["arc_id"] == "a2"


# ── append_scene ──────────────────────────────────────────────────────────────

def test_append_scene_adds_to_arc(db):
    plot_arc.create_arc("a1", "Titolo", ["Alice"])
    f = _scene_file(db)
    with patch(_GROQ, return_value="mock summary"):
        plot_arc.append_scene("a1", f)
    result = plot_arc.get_arc("a1")
    assert len(result["scenes"]) == 1


def test_append_scene_returns_dict(db):
    plot_arc.create_arc("a1", "Titolo", ["Alice"])
    f = _scene_file(db)
    with patch(_GROQ, return_value="mock summary"):
        result = plot_arc.append_scene("a1", f)
    assert isinstance(result, dict)
    assert "arc_id" in result


def test_append_scene_with_summary(db):
    plot_arc.create_arc("a1", "Titolo", ["Alice"])
    f = _scene_file(db)
    plot_arc.append_scene("a1", f, scene_summary="X")
    result = plot_arc.get_arc("a1")
    assert result["scenes"][0]["scene_summary"] == "X"


def test_append_scene_file_not_found_returns_empty(db):
    plot_arc.create_arc("a1", "Titolo", [])
    result = plot_arc.append_scene("a1", "/nonexistent/scene.md")
    assert result == {}


# ── regenerate_summary ────────────────────────────────────────────────────────

def test_regenerate_summary_arc_not_found_returns_empty(db):
    result = plot_arc.regenerate_summary("nonexistent-arc")
    assert result == ""


def test_regenerate_summary_arc_no_scenes_returns_empty(db):
    plot_arc.create_arc("a1", "Titolo", [])
    result = plot_arc.regenerate_summary("a1")
    assert result == ""


def test_regenerate_summary_with_scenes_calls_groq(db):
    plot_arc.create_arc("a1", "Titolo", [])
    f = _scene_file(db)
    plot_arc.append_scene("a1", f, scene_summary="Battaglia epica.")
    with patch(_GROQ, return_value="Arc summary here") as mock_groq:
        result = plot_arc.regenerate_summary("a1")
    mock_groq.assert_called_once()
    assert result == "Arc summary here"


# ── detect_open_threads ───────────────────────────────────────────────────────

def test_detect_open_threads_no_arc_returns_empty(db):
    assert plot_arc.detect_open_threads("nonexistent") == []


def test_detect_open_threads_no_scenes_returns_empty(db):
    plot_arc.create_arc("a1", "Titolo", [])
    assert plot_arc.detect_open_threads("a1") == []


def test_detect_open_threads_finds_unresolved_keyword(db):
    plot_arc.create_arc("a1", "Titolo", [])
    f_path = db / "s2.md"
    f_path.write_text("Alice is missing and the quest continues.")
    plot_arc.append_scene("a1", str(f_path), scene_summary="Alice is missing and the quest continues.")
    threads = plot_arc.detect_open_threads("a1")
    thread_texts = [t["thread"] for t in threads]
    assert any("missing" in t.lower() or "quest" in t.lower() for t in thread_texts)


# ── search_arcs_by_topic ──────────────────────────────────────────────────────

def test_search_arcs_by_topic_chromadb_unavailable_returns_empty(db):
    with patch("app.calliope_shell.plot_arc._arc_chroma_client", side_effect=Exception("ChromaDB not available")):
        result = plot_arc.search_arcs_by_topic("battle")
    assert result == []


# ── coverage gaps ─────────────────────────────────────────────────────────────

_AT = "app.calliope_shell.audit_trail.log_event"


def test_groq_ask_happy_path_returns_content(db):
    """_groq_ask lines 99-107: requests.post ok=True con content."""
    mock_resp = type("R", (), {"ok": True, "json": lambda self: {"content": "test content"}})()
    with patch("app.calliope_shell.plot_arc.requests.post", return_value=mock_resp):
        from app.calliope_shell.plot_arc import _groq_ask
        result = _groq_ask("test prompt")
    assert result == "test content"


def test_groq_ask_result_key_fallback(db):
    """_groq_ask: se content manca, usa result."""
    mock_resp = type("R", (), {"ok": True, "json": lambda self: {"result": "from result"}})()
    with patch("app.calliope_shell.plot_arc.requests.post", return_value=mock_resp):
        from app.calliope_shell.plot_arc import _groq_ask
        result = _groq_ask("test prompt")
    assert result == "from result"


def test_groq_ask_exception_returns_empty(db):
    """_groq_ask lines 108-110: exception → returns ''."""
    with patch("app.calliope_shell.plot_arc.requests.post", side_effect=OSError("timeout")):
        from app.calliope_shell.plot_arc import _groq_ask
        result = _groq_ask("test prompt")
    assert result == ""


def test_create_arc_audit_exception_silenced(db):
    """Lines 130-131: exception in audit block è silenziata."""
    with patch(_AT, side_effect=RuntimeError("audit fail")):
        result = plot_arc.create_arc("x1", "T", ["A"])
    assert result["arc_id"] == "x1"


def test_append_scene_audit_exception_silenced(db, tmp_path):
    """Lines 209-210: exception in audit block è silenziata."""
    scene_file = _scene_file(tmp_path)
    plot_arc.create_arc("a1", "T", ["Alice"])
    with patch(_AT, side_effect=RuntimeError("audit fail")):
        result = plot_arc.append_scene("a1", scene_file, "summary")
    assert result.get("arc_id") == "a1"


def test_regenerate_summary_audit_exception_silenced(db, tmp_path):
    """Lines 245-246: exception in audit block è silenziata."""
    scene_file = _scene_file(tmp_path)
    plot_arc.create_arc("a1", "T", ["Alice"])
    plot_arc.append_scene("a1", scene_file, "summary text")
    with patch(_GROQ, return_value="summary"), \
         patch(_AT, side_effect=RuntimeError("audit fail")):
        result = plot_arc.regenerate_summary("a1")
    assert isinstance(result, str)


def test_propose_next_scene_returns_valid_type(db):
    """Lines 286-319: propose_next_scene con risposta groq valida."""
    plot_arc.create_arc("a1", "Arc", ["Hero"])
    groq_response = "scene_type: action_combat\nprompt: The battle begins in the forest clearing."
    with patch(_GROQ, return_value=groq_response):
        result = plot_arc.propose_next_scene("a1", hint="escalate tension")
    assert result["scene_type"] == "action_combat"
    assert "forest" in result["prompt_seed"]
    assert result["hint_used"] == "escalate tension"


def test_propose_next_scene_invalid_type_defaults_to_mystery(db):
    """propose_next_scene: scene_type invalido → default mystery_investigation."""
    plot_arc.create_arc("a1", "Arc", ["Hero"])
    with patch(_GROQ, return_value="scene_type: invalid_type\nprompt: Some scene."):
        result = plot_arc.propose_next_scene("a1")
    assert result["scene_type"] == "mystery_investigation"


def test_propose_next_scene_empty_groq_uses_fallback(db):
    """propose_next_scene: groq vuoto → fallback prompt."""
    plot_arc.create_arc("a1", "Arc", ["Hero"])
    with patch(_GROQ, return_value=""):
        result = plot_arc.propose_next_scene("a1")
    assert "Continue the arc" in result["prompt_seed"]


def test_search_arcs_by_topic_inner_except_covered(db):
    """Lines 347-348: inner except in get_or_create_collection."""
    call_count = [0]
    mock_col = type("Col", (), {
        "upsert": lambda *a, **kw: None,
        "query": lambda *a, **kw: {"ids": [[]], "documents": [[]]},
    })()

    def get_or_create_side_effect(name):
        call_count[0] += 1
        if call_count[0] == 1:
            raise Exception("chroma busy")
        return mock_col

    mock_client = type("C", (), {"get_or_create_collection": get_or_create_side_effect})()
    with patch("app.calliope_shell.plot_arc._arc_chroma_client", return_value=mock_client):
        result = plot_arc.search_arcs_by_topic("test query")
    assert isinstance(result, list)


def test_search_arcs_by_topic_result_loop_covered(db):
    """Line 368: out.append(...) in result loop."""
    plot_arc.create_arc("a1", "The Dragon Arc", ["Hero"])
    mock_col = type("Col", (), {
        "upsert": lambda *a, **kw: None,
        "query": lambda *a, **kw: {
            "ids": [["a1"]], "documents": [["The Dragon Arc — Hero fights the dragon"]],
        },
    })()
    mock_client = type("C", (), {
        "get_or_create_collection": lambda *a, **kw: mock_col,
    })()
    with patch("app.calliope_shell.plot_arc._arc_chroma_client", return_value=mock_client):
        result = plot_arc.search_arcs_by_topic("dragon")
    assert len(result) == 1
    assert result[0]["arc_id"] == "a1"
    assert "Dragon" in result[0]["summary_excerpt"]
