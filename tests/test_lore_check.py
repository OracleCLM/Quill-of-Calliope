"""Sprint D4 — POST /api/lore/check test suite."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


def _make_app():
    from app.calliope_shell.server import create_app
    app, _ = create_app()
    app.config["TESTING"] = True
    return app


# TL1 — text required
def test_tl1_lore_check_requires_text():
    app = _make_app()
    with app.test_client() as c:
        r = c.post("/api/lore/check", json={})
    assert r.status_code == 400
    assert "text" in r.get_json()["error"]


# TL2 — no lore in ChromaDB returns coherent=true with note
def test_tl2_lore_check_no_lore():
    with patch("app.calliope_shell.server._search_lore", return_value=[]):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/lore/check", json={"text": "Aurora cast a fire spell."})

    assert r.status_code == 200
    data = r.get_json()
    assert data["coherent"] is True
    assert "note" in data


# TL3 — coherent text returns no issues
def test_tl3_lore_check_coherent():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": '{"coherent": true, "issues": []}'}
    mock_resp.raise_for_status = MagicMock()

    with patch("app.calliope_shell.server._search_lore", return_value=["The Yokai realm is ancient."]), \
         patch("requests.post", return_value=mock_resp):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/lore/check", json={"text": "Aurora walked through the ancient Yokai realm."})

    assert r.status_code == 200
    data = r.get_json()
    assert data["coherent"] is True
    assert data["issues"] == []
    assert len(data["checked_against"]) > 0


# TL4 — incoherent text returns issues
def test_tl4_lore_check_incoherent():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "result": '{"coherent": false, "issues": [{"severity": "error", "description": "Aurora is yokai, not human", "lore_ref": "characters/aurora"}]}'
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("app.calliope_shell.server._search_lore", return_value=["Aurora is a yokai queen."]), \
         patch("requests.post", return_value=mock_resp):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/lore/check", json={"text": "Aurora, the human warrior, drew her sword."})

    assert r.status_code == 200
    data = r.get_json()
    assert data["coherent"] is False
    assert len(data["issues"]) > 0
    assert data["issues"][0]["severity"] == "error"


# TL5 — uses openrouter via llm_review
def test_tl5_lore_check_uses_openrouter():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": '{"coherent": true, "issues": []}'}
    mock_resp.raise_for_status = MagicMock()

    captured = {}

    def capture_post(url, json=None, **kw):
        captured["url"] = url
        captured["provider"] = json.get("provider", "") if json else ""
        return mock_resp

    with patch("app.calliope_shell.server._search_lore", return_value=["lore"]), \
         patch("requests.post", side_effect=capture_post):
        app = _make_app()
        with app.test_client() as c:
            c.post("/api/lore/check", json={"text": "test"})

    assert "/llm_review" in captured.get("url", "")
    assert captured.get("provider") == "openrouter"


# TL6 — gateway down returns 503
def test_tl6_lore_check_gateway_down():
    import requests as _req
    with patch("app.calliope_shell.server._search_lore", return_value=["lore"]), \
         patch("requests.post", side_effect=_req.exceptions.ConnectionError("down")):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/lore/check", json={"text": "test"})
    assert r.status_code == 503


# TL7 — audit_trail called
def test_tl7_lore_check_audit():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": '{"coherent": true, "issues": []}'}
    mock_resp.raise_for_status = MagicMock()

    with patch("app.calliope_shell.server._search_lore", return_value=["lore"]), \
         patch("requests.post", return_value=mock_resp), \
         patch("app.calliope_shell.audit_trail.log_event") as mock_audit:
        app = _make_app()
        with app.test_client() as c:
            c.post("/api/lore/check", json={"text": "test"})

    mock_audit.assert_called_once()
    assert mock_audit.call_args[0][0] == "lore.check"
