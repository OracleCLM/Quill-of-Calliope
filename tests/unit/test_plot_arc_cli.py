"""
Unit test per scripts/plot_arc_cli.py.
Tutte le cmd_* delegano a app.calliope_shell.plot_arc — mock a livello modulo.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.plot_arc_cli import (
    cmd_create,
    cmd_append,
    cmd_summary,
    cmd_threads,
    cmd_continue,
    cmd_list,
    cmd_search,
    cmd_get,
    main as cli_main,
)

_PA = "scripts.plot_arc_cli.plot_arc"

_ARC = {
    "arc_id": "arc-01",
    "title": "La caduta di Aetheron",
    "status": "active",
    "chars": ["Aurora", "Luna"],
    "scenes": [],
    "summary": "",
}


# ── cmd_create ────────────────────────────────────────────────────────────────

def test_cmd_create_success(capsys):
    ns = SimpleNamespace(arc_id="arc-01", title="La caduta di Aetheron", char="Aurora,Luna")
    with patch(_PA) as pa:
        pa.create_arc.return_value = _ARC
        ret = cmd_create(ns)
    assert ret == 0
    assert "arc-01" in capsys.readouterr().out


def test_cmd_create_failure_returns_1(capsys):
    ns = SimpleNamespace(arc_id="", title="", char="")
    with patch(_PA) as pa:
        pa.create_arc.return_value = None
        ret = cmd_create(ns)
    assert ret == 1
    assert "ERROR" in capsys.readouterr().err


def test_cmd_create_empty_char_list(capsys):
    ns = SimpleNamespace(arc_id="arc-02", title="Titolo", char=None)
    with patch(_PA) as pa:
        pa.create_arc.return_value = {**_ARC, "arc_id": "arc-02"}
        ret = cmd_create(ns)
    assert ret == 0
    pa.create_arc.assert_called_once_with("arc-02", "Titolo", [])


# ── cmd_append ────────────────────────────────────────────────────────────────

def test_cmd_append_success(capsys):
    ns = SimpleNamespace(arc_id="arc-01", scene_md="scene01.md")
    with patch(_PA) as pa:
        pa.append_scene.return_value = {"scene_order": 1, "scene_summary": "Intro battaglia"}
        ret = cmd_append(ns)
    assert ret == 0
    assert "Intro battaglia" in capsys.readouterr().out


def test_cmd_append_failure_returns_1(capsys):
    ns = SimpleNamespace(arc_id="arc-01", scene_md="missing.md")
    with patch(_PA) as pa:
        pa.append_scene.return_value = None
        ret = cmd_append(ns)
    assert ret == 1
    assert "ERROR" in capsys.readouterr().err


# ── cmd_summary ───────────────────────────────────────────────────────────────

def test_cmd_summary_success(capsys):
    ns = SimpleNamespace(arc_id="arc-01")
    with patch(_PA) as pa:
        pa.regenerate_summary.return_value = "Riassunto epico."
        ret = cmd_summary(ns)
    assert ret == 0
    assert "Riassunto epico" in capsys.readouterr().out


def test_cmd_summary_failure_returns_1(capsys):
    ns = SimpleNamespace(arc_id="arc-nonexistent")
    with patch(_PA) as pa:
        pa.regenerate_summary.return_value = None
        ret = cmd_summary(ns)
    assert ret == 1
    assert "ERROR" in capsys.readouterr().err


# ── cmd_threads ───────────────────────────────────────────────────────────────

def test_cmd_threads_with_threads(capsys):
    ns = SimpleNamespace(arc_id="arc-01")
    threads = [{"type": "conflict", "thread": "Chi è il traditore?", "last_scene_idx": 3}]
    with patch(_PA) as pa:
        pa.detect_open_threads.return_value = threads
        ret = cmd_threads(ns)
    assert ret == 0
    assert "traditore" in capsys.readouterr().out


def test_cmd_threads_empty(capsys):
    ns = SimpleNamespace(arc_id="arc-01")
    with patch(_PA) as pa:
        pa.detect_open_threads.return_value = []
        ret = cmd_threads(ns)
    assert ret == 0
    assert "No open threads" in capsys.readouterr().out


# ── cmd_continue ──────────────────────────────────────────────────────────────

def test_cmd_continue_success(capsys):
    ns = SimpleNamespace(arc_id="arc-01", hint=None)
    with patch(_PA) as pa:
        pa.propose_next_scene.return_value = {
            "scene_type": "confronto",
            "prompt_seed": "Luna affronta Aurora",
            "hint_used": None,
        }
        ret = cmd_continue(ns)
    assert ret == 0
    assert "confronto" in capsys.readouterr().out


def test_cmd_continue_with_hint(capsys):
    ns = SimpleNamespace(arc_id="arc-01", hint="rivelazione tradimento")
    with patch(_PA) as pa:
        pa.propose_next_scene.return_value = {
            "scene_type": "rivelazione",
            "prompt_seed": "Aurora scopre la verità",
            "hint_used": "rivelazione tradimento",
        }
        ret = cmd_continue(ns)
    out = capsys.readouterr().out
    assert ret == 0
    assert "hint applied" in out


def test_cmd_continue_failure_returns_1(capsys):
    ns = SimpleNamespace(arc_id="ghost", hint=None)
    with patch(_PA) as pa:
        pa.propose_next_scene.return_value = None
        ret = cmd_continue(ns)
    assert ret == 1
    assert "ERROR" in capsys.readouterr().err


# ── cmd_list ──────────────────────────────────────────────────────────────────

def test_cmd_list_empty(capsys):
    ns = SimpleNamespace(status=None)
    with patch(_PA) as pa:
        pa.list_arcs.return_value = []
        ret = cmd_list(ns)
    assert ret == 0
    assert "No arcs" in capsys.readouterr().out


def test_cmd_list_with_arcs(capsys):
    ns = SimpleNamespace(status="active")
    arcs = [_ARC, {**_ARC, "arc_id": "arc-02", "title": "Secondo arco"}]
    with patch(_PA) as pa:
        pa.list_arcs.return_value = arcs
        ret = cmd_list(ns)
    out = capsys.readouterr().out
    assert ret == 0
    assert "arc-01" in out
    assert "arc-02" in out


# ── cmd_search ────────────────────────────────────────────────────────────────

def test_cmd_search_no_results(capsys):
    ns = SimpleNamespace(query="fantasma misterioso")
    with patch(_PA) as pa:
        pa.search_arcs_by_topic.return_value = []
        ret = cmd_search(ns)
    assert ret == 0
    assert "No matching" in capsys.readouterr().out


def test_cmd_search_with_results(capsys):
    ns = SimpleNamespace(query="drago")
    with patch(_PA) as pa:
        pa.search_arcs_by_topic.return_value = [
            {"arc_id": "arc-01", "summary_excerpt": "Il drago risvegliato"},
        ]
        ret = cmd_search(ns)
    assert ret == 0
    assert "drago" in capsys.readouterr().out


# ── cmd_get ───────────────────────────────────────────────────────────────────

def test_cmd_get_found(capsys):
    ns = SimpleNamespace(arc_id="arc-01")
    with patch(_PA) as pa:
        pa.get_arc.return_value = _ARC
        ret = cmd_get(ns)
    out = capsys.readouterr().out
    assert ret == 0
    assert "arc-01" in out
    assert "La caduta di Aetheron" in out


def test_cmd_get_not_found_returns_1(capsys):
    ns = SimpleNamespace(arc_id="ghost")
    with patch(_PA) as pa:
        pa.get_arc.return_value = None
        ret = cmd_get(ns)
    assert ret == 1
    assert "ERROR" in capsys.readouterr().err


# ── main/parser ───────────────────────────────────────────────────────────────

def test_main_parser_create(monkeypatch):
    monkeypatch.setattr(
        "sys.argv", ["plot_arc_cli.py", "create", "arc-01", "Titolo del cammino"]
    )
    with patch(_PA) as pa:
        pa.create_arc.return_value = _ARC
        ret = cli_main()
    assert ret == 0


def test_main_parser_list(monkeypatch):
    monkeypatch.setattr("sys.argv", ["plot_arc_cli.py", "list"])
    with patch(_PA) as pa:
        pa.list_arcs.return_value = []
        ret = cli_main()
    assert ret == 0


# ── _print_arc: scenes + summary branches (lines 33-34, 37) ──────────────────

def test_cmd_get_prints_scenes_and_summary(capsys):
    arc_with_data = {
        **_ARC,
        "scenes": [{"scene_order": 1, "scene_summary": "La battaglia finale"}],
        "summary": "Un arco epico sulla caduta di Aetheron.",
    }
    ns = SimpleNamespace(arc_id="arc-01")
    with patch(_PA) as pa:
        pa.get_arc.return_value = arc_with_data
        ret = cmd_get(ns)
    assert ret == 0
    out = capsys.readouterr().out
    assert "La battaglia finale" in out
    assert "Un arco epico" in out
