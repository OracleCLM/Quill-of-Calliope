"""
Unit test per app/db/scenes.py — list_scenes, assign_scene_to_arc.

Usa la fixture db_connection (SQLite in-memory con schema completo).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.arcs import create_arc
from app.db.scenes import assign_scene_to_arc, list_scenes
from app.db.messages import add_message
from tests.unit.conftest import add_scene


# ── list_scenes ───────────────────────────────────────────────────────────────

def test_list_scenes_empty(db_connection):
    conn = db_connection["conn"]
    assert list_scenes(conn) == []


def test_list_scenes_returns_all(db_connection):
    conn = db_connection["conn"]
    add_scene(conn, title="Alpha")
    add_scene(conn, title="Beta")
    result = list_scenes(conn)
    assert len(result) == 2


def test_list_scenes_dict_has_id_title(db_connection):
    conn = db_connection["conn"]
    add_scene(conn, title="Mia scena")
    result = list_scenes(conn)
    assert result[0]["title"] == "Mia scena"
    assert "id" in result[0]


def test_list_scenes_title_filter_match(db_connection):
    conn = db_connection["conn"]
    add_scene(conn, title="Battaglia nel bosco")
    add_scene(conn, title="Incontro in città")
    result = list_scenes(conn, title_contains="Battaglia")
    assert len(result) == 1
    assert result[0]["title"] == "Battaglia nel bosco"


def test_list_scenes_title_filter_no_match(db_connection):
    conn = db_connection["conn"]
    add_scene(conn, title="Scena unica")
    result = list_scenes(conn, title_contains="nessuna")
    assert result == []


def test_list_scenes_filter_case_insensitive(db_connection):
    conn = db_connection["conn"]
    add_scene(conn, title="Duello al tramonto")
    result = list_scenes(conn, title_contains="duello")
    assert len(result) >= 1


def test_list_scenes_filter_substring(db_connection):
    conn = db_connection["conn"]
    add_scene(conn, title="La grande battaglia")
    result = list_scenes(conn, title_contains="grande")
    assert len(result) == 1


# ── assign_scene_to_arc ───────────────────────────────────────────────────────

def test_assign_scene_to_arc_returns_true(db_connection):
    conn = db_connection["conn"]
    scene_id = add_scene(conn)
    arc_id = create_arc(conn, title="Arco 1")
    result = assign_scene_to_arc(conn, scene_id, arc_id)
    assert result is True


def test_assign_scene_to_arc_scene_not_found(db_connection):
    conn = db_connection["conn"]
    arc_id = create_arc(conn, title="Arco 1")
    result = assign_scene_to_arc(conn, "ghost-id", arc_id)
    assert result is False


def test_assign_scene_to_arc_persists(db_connection):
    conn = db_connection["conn"]
    scene_id = add_scene(conn)
    arc_id = create_arc(conn, title="Arco X")
    assign_scene_to_arc(conn, scene_id, arc_id)
    scenes = list_scenes(conn)
    assert scenes[0]["arc_id"] == arc_id


def test_assign_scene_to_arc_none_removes(db_connection):
    conn = db_connection["conn"]
    scene_id = add_scene(conn)
    arc_id = create_arc(conn, title="Arco Y")
    assign_scene_to_arc(conn, scene_id, arc_id)
    assign_scene_to_arc(conn, scene_id, None)
    scenes = list_scenes(conn)
    assert scenes[0]["arc_id"] is None


# ── nuovi campi message_count + is_readonly ───────────────────────────────────

def test_list_scenes_message_count_zero_when_no_messages(db_connection):
    conn = db_connection["conn"]
    add_scene(conn, title="Scena vuota")
    result = list_scenes(conn)
    assert result[0]["message_count"] == 0


def test_list_scenes_message_count_reflects_messages(db_connection):
    conn = db_connection["conn"]
    scene_id = add_scene(conn, title="Scena piena")
    add_message(conn, scene_id=scene_id, author_name="Alice", content_original="ciao", position_order=0)
    add_message(conn, scene_id=scene_id, author_name="Bob", content_original="hi", position_order=1)
    result = list_scenes(conn)
    assert result[0]["message_count"] == 2


def test_list_scenes_is_readonly_default_false(db_connection):
    conn = db_connection["conn"]
    add_scene(conn, title="Scena normale")
    result = list_scenes(conn)
    assert result[0]["is_readonly"] == 0
