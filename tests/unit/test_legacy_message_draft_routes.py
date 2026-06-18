"""GAP-78: test per /api/messages/recent, /api/messages/next e /api/draft."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import requests as _req

from app.calliope_shell.server import create_app


def _app_client():
    app, _ = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _mock_ok(text="risposta"):
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"result": text}
    mock.raise_for_status = MagicMock()
    return mock


# ── GET /api/messages/recent ──────────────────────────────────────────────────


def test_messages_recent_always_200():
    r = _app_client().get("/api/messages/recent")
    assert r.status_code == 200


def test_messages_recent_has_required_keys():
    data = _app_client().get("/api/messages/recent").get_json()
    assert "messages" in data
    assert "count" in data


def test_messages_recent_messages_is_list():
    data = _app_client().get("/api/messages/recent").get_json()
    assert isinstance(data["messages"], list)


def test_messages_recent_limit_param_accepted():
    r = _app_client().get("/api/messages/recent?limit=5")
    assert r.status_code == 200


# ── POST /api/messages/next ───────────────────────────────────────────────────


def test_messages_next_missing_char_returns_400():
    r = _app_client().post("/api/messages/next", json={"scene_id": "s1"})
    assert r.status_code == 400


def test_messages_next_gateway_down_returns_503():
    with patch("requests.post", side_effect=_req.exceptions.ConnectionError):
        r = _app_client().post("/api/messages/next", json={"char": "Aurora"})
    assert r.status_code == 503


def test_messages_next_ok_returns_next_msg():
    with patch("requests.post", return_value=_mock_ok("Aurora sorride.")):
        r = _app_client().post("/api/messages/next", json={"char": "Aurora"})
    assert r.status_code == 200
    data = r.get_json()
    assert "next_msg" in data
    assert data["char"] == "Aurora"


# ── POST /api/draft ───────────────────────────────────────────────────────────


def test_draft_missing_intent_returns_400():
    r = _app_client().post("/api/draft", json={"scene_id": "s1"})
    assert r.status_code == 400


def test_draft_empty_intent_returns_400():
    r = _app_client().post("/api/draft", json={"intent_it": ""})
    assert r.status_code == 400


def test_draft_gateway_down_returns_503():
    with (
        patch("requests.post", side_effect=_req.exceptions.ConnectionError),
        patch("app.calliope_shell.server._search_lore", return_value=[]),
    ):
        r = _app_client().post("/api/draft", json={"intent_it": "apri la scena"})
    assert r.status_code == 503


def test_draft_ok_returns_draft_text():
    with (
        patch("requests.post", return_value=_mock_ok("Bozza generata.")),
        patch("app.calliope_shell.server._search_lore", return_value=[]),
    ):
        r = _app_client().post("/api/draft", json={"intent_it": "apri la scena"})
    assert r.status_code == 200
    data = r.get_json()
    assert "draft_text" in data
    assert data["draft_text"] == "Bozza generata."


def test_draft_ok_includes_model_used():
    with (
        patch("requests.post", return_value=_mock_ok("Testo.")),
        patch("app.calliope_shell.server._search_lore", return_value=[]),
    ):
        data = _app_client().post("/api/draft", json={"intent_it": "scena drammatica"}).get_json()
    assert "model_used" in data


def test_draft_ok_includes_context_used():
    with (
        patch("requests.post", return_value=_mock_ok("Testo.")),
        patch("app.calliope_shell.server._search_lore", return_value=[]),
    ):
        data = _app_client().post("/api/draft", json={"intent_it": "scena"}).get_json()
    assert "context_used" in data
