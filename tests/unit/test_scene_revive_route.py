"""Test happy-path e edge case per POST /api/scene/revive."""
from __future__ import annotations

import yaml
from unittest.mock import MagicMock, patch

from app.calliope_shell.server import create_app

_SRV = "app.calliope_shell.server"


def _client():
    app, _ = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _scene_yaml(tmp_path, scene_id="forest_hunt", **overrides):
    data = {
        "scene_id": scene_id,
        "title": "The Forest Hunt",
        "status": "dormant",
        "summary": "The party tracks a beast through the dark woods.",
        "participants": ["Aurora", "Kael"],
        "last_msg_excerpt": "The beast roared into the night.",
    }
    data.update(overrides)
    p = tmp_path / f"{scene_id}.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")
    return p


def _mock_llm_response(text="Revival summary here."):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"result": text}
    return mock_resp


def test_revive_happy_path_200(tmp_path):
    _scene_yaml(tmp_path)
    mock_chroma = MagicMock()
    mock_chroma.get_collection.side_effect = Exception("chroma down")

    with _client() as c:
        with patch(f"{_SRV}._SCENES_DIR", tmp_path), \
             patch(f"{_SRV}._chroma_client", return_value=mock_chroma), \
             patch(f"{_SRV}._load_char_sheets", return_value=[]), \
             patch(f"{_SRV}._search_lore", return_value=[]), \
             patch(f"{_SRV}.requests.post", return_value=_mock_llm_response("Revival text.")):
            r = c.post("/api/scene/revive", json={"scene_id": "forest_hunt"})

    assert r.status_code == 200


def test_revive_response_contains_scene_context(tmp_path):
    _scene_yaml(tmp_path)

    with _client() as c:
        with patch(f"{_SRV}._SCENES_DIR", tmp_path), \
             patch(f"{_SRV}._chroma_client", side_effect=Exception("down")), \
             patch(f"{_SRV}._load_char_sheets", return_value=[]), \
             patch(f"{_SRV}._search_lore", return_value=[]), \
             patch(f"{_SRV}.requests.post", return_value=_mock_llm_response()):
            r = c.post("/api/scene/revive", json={"scene_id": "forest_hunt"})

    data = r.get_json()
    ctx = data["scene_context"]
    assert ctx["scene_id"] == "forest_hunt"
    assert ctx["title"] == "The Forest Hunt"
    assert ctx["status"] == "dormant"
    assert "beast" in ctx["summary"]


def test_revive_suggested_reentry_from_llm(tmp_path):
    _scene_yaml(tmp_path)

    with _client() as c:
        with patch(f"{_SRV}._SCENES_DIR", tmp_path), \
             patch(f"{_SRV}._chroma_client", side_effect=Exception("down")), \
             patch(f"{_SRV}._load_char_sheets", return_value=[]), \
             patch(f"{_SRV}._search_lore", return_value=[]), \
             patch(f"{_SRV}.requests.post", return_value=_mock_llm_response("Re-entry idea A and B.")):
            r = c.post("/api/scene/revive", json={"scene_id": "forest_hunt"})

    data = r.get_json()
    assert data["suggested_reentry"] == "Re-entry idea A and B."
    assert data["model_used"] == "groq/llama-3.3-70b-versatile"


def test_revive_llm_failure_returns_fallback(tmp_path):
    _scene_yaml(tmp_path)

    with _client() as c:
        with patch(f"{_SRV}._SCENES_DIR", tmp_path), \
             patch(f"{_SRV}._chroma_client", side_effect=Exception("down")), \
             patch(f"{_SRV}._load_char_sheets", return_value=[]), \
             patch(f"{_SRV}._search_lore", return_value=[]), \
             patch(f"{_SRV}.requests.post", side_effect=Exception("LLM offline")):
            r = c.post("/api/scene/revive", json={"scene_id": "forest_hunt"})

    assert r.status_code == 200
    data = r.get_json()
    assert "unavailable" in data["suggested_reentry"].lower()


def test_revive_partial_scene_id_match(tmp_path):
    _scene_yaml(tmp_path, scene_id="act1_forest_hunt_opening")

    with _client() as c:
        with patch(f"{_SRV}._SCENES_DIR", tmp_path), \
             patch(f"{_SRV}._chroma_client", side_effect=Exception("down")), \
             patch(f"{_SRV}._load_char_sheets", return_value=[]), \
             patch(f"{_SRV}._search_lore", return_value=[]), \
             patch(f"{_SRV}.requests.post", return_value=_mock_llm_response()):
            r = c.post("/api/scene/revive", json={"scene_id": "forest_hunt"})

    assert r.status_code == 200
    data = r.get_json()
    assert data["scene_context"]["scene_id"] == "act1_forest_hunt_opening"
