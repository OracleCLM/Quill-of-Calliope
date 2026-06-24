"""
Test per gli endpoint arc legacy di server.py (usa plot_arc module, non arcs_db_routes):
  GET  /api/arc                     → list_arcs
  GET  /api/arc/<id>                → get_arc (200|404)
  POST /api/arc/<id>/append         → append_scene (200|400)
  POST /api/arc/<id>/summary        → regenerate_summary
  GET  /api/arc/<id>/threads        → detect_open_threads
  POST /api/arc/<id>/continue       → propose_next_scene (200|503)
  POST /api/arc/search              → search_arcs_by_topic (200|400)

Tutti i metodi plot_arc sono mockati via patch sul modulo originale.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch

from app.calliope_shell.server import create_app

_PA = "app.calliope_shell.plot_arc"
_SRV = "app.calliope_shell.server"

_ARC = {"arc_id": "arc-01", "title": "L'alba del drago", "status": "active"}


@pytest.fixture
def client():
    app, _ = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── GET /api/arc ──────────────────────────────────────────────────────────────

def test_arc_list_empty(client):
    with patch(f"{_PA}.list_arcs", return_value=[]):
        r = client.get("/api/arc")
    assert r.status_code == 200
    assert r.get_json() == []


def test_arc_list_with_status_filter(client):
    with patch(f"{_PA}.list_arcs", return_value=[_ARC]) as mock_list:
        r = client.get("/api/arc?status=active")
    assert r.status_code == 200
    arcs = r.get_json()
    assert len(arcs) == 1
    assert arcs[0]["arc_id"] == "arc-01"
    mock_list.assert_called_once_with(status="active")


# ── GET /api/arc/<id> ─────────────────────────────────────────────────────────

def test_arc_get_found_200(client):
    with patch(f"{_PA}.get_arc", return_value=_ARC):
        r = client.get("/api/arc/arc-01")
    assert r.status_code == 200
    assert r.get_json()["arc_id"] == "arc-01"


def test_arc_get_not_found_404(client):
    with patch(f"{_PA}.get_arc", return_value=None):
        r = client.get("/api/arc/nonexistent")
    assert r.status_code == 404
    assert "error" in r.get_json()


# ── POST /api/arc/<id>/append ─────────────────────────────────────────────────

def test_arc_append_success_200(client):
    expected = {**_ARC, "scenes": ["scenes/scene01.md"]}
    with patch(f"{_PA}.append_scene", return_value=expected):
        r = client.post("/api/arc/arc-01/append", json={"scene_md_path": "scenes/scene01.md"})
    assert r.status_code == 200
    assert "scenes" in r.get_json()


def test_arc_append_missing_scene_path_400(client):
    r = client.post("/api/arc/arc-01/append", json={})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_arc_append_failure_400(client):
    with patch(f"{_PA}.append_scene", return_value=None):
        r = client.post("/api/arc/arc-01/append", json={"scene_md_path": "missing.md"})
    assert r.status_code == 400


# ── POST /api/arc/<id>/summary ────────────────────────────────────────────────

def test_arc_summary_200(client):
    with patch(f"{_PA}.regenerate_summary", return_value="Riassunto dell'arco."):
        r = client.post("/api/arc/arc-01/summary")
    assert r.status_code == 200
    data = r.get_json()
    assert data["arc_id"] == "arc-01"
    assert data["summary"] == "Riassunto dell'arco."


# ── GET /api/arc/<id>/threads ─────────────────────────────────────────────────

def test_arc_threads_200(client):
    threads = [{"thread": "Il tradimento di Lyra", "status": "open"}]
    with patch(f"{_PA}.detect_open_threads", return_value=threads):
        r = client.get("/api/arc/arc-01/threads")
    assert r.status_code == 200
    data = r.get_json()
    assert data["arc_id"] == "arc-01"
    assert len(data["threads"]) == 1


# ── POST /api/arc/<id>/continue ───────────────────────────────────────────────

def test_arc_continue_success_200(client):
    proposal = {"title": "La resa dei conti", "synopsis": "Confronto finale."}
    with patch(f"{_PA}.propose_next_scene", return_value=proposal):
        r = client.post("/api/arc/arc-01/continue", json={"hint": "drago"})
    assert r.status_code == 200
    assert r.get_json()["title"] == "La resa dei conti"


def test_arc_continue_no_result_503(client):
    with patch(f"{_PA}.propose_next_scene", return_value=None):
        r = client.post("/api/arc/arc-01/continue", json={})
    assert r.status_code == 503


# ── POST /api/arc/search ──────────────────────────────────────────────────────

def test_arc_search_success_200(client):
    with patch(f"{_PA}.search_arcs_by_topic", return_value=[_ARC]):
        r = client.post("/api/arc/search", json={"query": "drago"})
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data["results"], list)
    assert data["results"][0]["arc_id"] == "arc-01"


def test_arc_search_missing_query_400(client):
    r = client.post("/api/arc/search", json={})
    assert r.status_code == 400
    assert "error" in r.get_json()
