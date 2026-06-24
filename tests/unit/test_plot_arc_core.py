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
