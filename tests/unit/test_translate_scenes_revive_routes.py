"""GAP-80: test per /api/translate, /api/scenes (GET) e /api/scene/revive."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import requests as _req

import app.calliope_shell.server as srv
from app.calliope_shell.server import create_app


def _client():
    app, _ = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _mock_ok(text="risposta"):
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"result": text}
    mock.raise_for_status = MagicMock()
    return mock


# ── POST /api/translate ───────────────────────────────────────────────────────


def test_translate_missing_text_returns_400():
    r = _client().post("/api/translate", json={})
    assert r.status_code == 400


def test_translate_invalid_direction_returns_400():
    r = _client().post("/api/translate", json={"text": "ciao", "direction": "XX_to_YY"})
    assert r.status_code == 400


def test_translate_gateway_down_returns_503():
    with patch("requests.post", side_effect=_req.exceptions.ConnectionError):
        r = _client().post("/api/translate", json={"text": "ciao", "direction": "IT_to_EN"})
    assert r.status_code == 503


def test_translate_ok_returns_translation():
    with patch("requests.post", return_value=_mock_ok("hello")):
        r = _client().post("/api/translate", json={"text": "ciao", "direction": "IT_to_EN"})
    assert r.status_code == 200
    data = r.get_json()
    assert "translation" in data
    assert data["translation"] == "hello"


def test_translate_en_to_it_direction_accepted():
    with patch("requests.post", return_value=_mock_ok("ciao")):
        r = _client().post("/api/translate", json={"text": "hello", "direction": "EN_to_IT"})
    assert r.status_code == 200


# ── GET /api/scenes ───────────────────────────────────────────────────────────


def test_scenes_list_returns_200(monkeypatch, tmp_path):
    monkeypatch.setattr(srv, "_SCENES_DIR", tmp_path)
    r = _client().get("/api/scenes")
    assert r.status_code == 200


def test_scenes_list_has_scenes_key(monkeypatch, tmp_path):
    monkeypatch.setattr(srv, "_SCENES_DIR", tmp_path)
    data = _client().get("/api/scenes").get_json()
    assert "scenes" in data
    assert "total" in data


def test_scenes_list_empty_without_drafts(monkeypatch, tmp_path):
    monkeypatch.setattr(srv, "_SCENES_DIR", tmp_path)
    data = _client().get("/api/scenes").get_json()
    assert data["scenes"] == []
    assert data["total"] == 0


def test_scenes_list_returns_draft_yaml(monkeypatch, tmp_path):
    (tmp_path / "scena1.draft.yaml").write_text("title: Scena Test\nparticipants: []\n")
    monkeypatch.setattr(srv, "_SCENES_DIR", tmp_path)
    data = _client().get("/api/scenes").get_json()
    assert data["total"] == 1


# ── POST /api/scene/revive ────────────────────────────────────────────────────


def test_scene_revive_missing_scene_id_returns_400():
    r = _client().post("/api/scene/revive", json={})
    assert r.status_code == 400


def test_scene_revive_scene_not_found_returns_404(monkeypatch, tmp_path):
    monkeypatch.setattr(srv, "_SCENES_DIR", tmp_path)
    r = _client().post("/api/scene/revive", json={"scene_id": "scena-inesistente"})
    assert r.status_code == 404


def test_scene_revive_found_gateway_down_graceful_200(monkeypatch, tmp_path):
    # LLM failure is non-fatal: route returns 200 with fallback suggested_reentry text
    (tmp_path / "scena_x.yaml").write_text("title: Test\nparticipants: []\nsummary: breve\n")
    monkeypatch.setattr(srv, "_SCENES_DIR", tmp_path)
    with (
        patch("requests.post", side_effect=_req.exceptions.ConnectionError),
        patch("app.calliope_shell.server._search_lore", return_value=[]),
    ):
        r = _client().post("/api/scene/revive", json={"scene_id": "scena_x"})
    assert r.status_code == 200
    data = r.get_json()
    assert "suggested_reentry" in data
    assert "LLM unavailable" in data["suggested_reentry"]
