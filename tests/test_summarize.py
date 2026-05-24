"""Sprint D2 — POST /api/summarize test suite."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


def _make_app():
    from app.calliope_shell.server import create_app
    app, _ = create_app()
    app.config["TESTING"] = True
    return app


# TS1 — text required
def test_ts1_summarize_requires_text():
    app = _make_app()
    with app.test_client() as c:
        r = c.post("/api/summarize", json={})
    assert r.status_code == 400
    assert "text" in r.get_json()["error"]


# TS2 — valid JSON response from LLM parsed correctly
def test_ts2_summarize_parses_json_response():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "result": '{"summary": "Kikyo left the shrine.", "key_facts": ["Kikyo departed", "Met Pdor"]}'
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/summarize", json={"text": "Long discord paste about Kikyo..."})

    assert r.status_code == 200
    data = r.get_json()
    assert data["summary"] == "Kikyo left the shrine."
    assert len(data["key_facts"]) == 2
    assert "word_count" in data
    assert data["model_used"] == "groq/llama-3.3-70b-versatile"


# TS3 — non-JSON LLM response falls back to raw text
def test_ts3_summarize_fallback_raw():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": "Just a plain summary without JSON."}
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/summarize", json={"text": "Some text to summarize"})

    assert r.status_code == 200
    data = r.get_json()
    assert data["summary"] == "Just a plain summary without JSON."
    assert data["key_facts"] == []


# TS4 — uses groq provider via llm_ask
def test_ts4_summarize_uses_groq():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": '{"summary": "ok", "key_facts": []}'}
    mock_resp.raise_for_status = MagicMock()

    captured = {}

    def capture_post(url, json=None, **kw):
        captured["url"] = url
        captured["provider"] = json.get("provider", "") if json else ""
        return mock_resp

    with patch("requests.post", side_effect=capture_post):
        app = _make_app()
        with app.test_client() as c:
            c.post("/api/summarize", json={"text": "test"})

    assert "/llm_ask" in captured.get("url", "")
    assert captured.get("provider") == "groq"


# TS5 — gateway down returns 503
def test_ts5_summarize_gateway_down():
    import requests as _req
    with patch("requests.post", side_effect=_req.exceptions.ConnectionError("down")):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/summarize", json={"text": "test"})
    assert r.status_code == 503


# TS6 — audit_trail called
def test_ts6_summarize_audit():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": '{"summary": "ok", "key_facts": []}'}
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp), \
         patch("app.calliope_shell.audit_trail.log_event") as mock_audit:
        app = _make_app()
        with app.test_client() as c:
            c.post("/api/summarize", json={"text": "test audit"})

    mock_audit.assert_called_once()
    assert mock_audit.call_args[0][0] == "summarize.run"


# TS7 — markdown-fenced JSON response is parsed
def test_ts7_summarize_strips_markdown_fences():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "result": '```json\n{"summary": "fenced", "key_facts": ["a"]}\n```'
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/summarize", json={"text": "test"})

    data = r.get_json()
    assert data["summary"] == "fenced"
    assert data["key_facts"] == ["a"]
