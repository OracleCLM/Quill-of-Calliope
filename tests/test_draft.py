"""Sprint D1 — POST /api/draft test suite."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


def _make_app():
    from app.calliope_shell.server import create_app
    app, _ = create_app()
    app.config["TESTING"] = True
    return app


# TD1 — intent_it required
def test_td1_draft_requires_intent():
    app = _make_app()
    with app.test_client() as c:
        r = c.post("/api/draft", json={"scene_id": "scene_003"})
    assert r.status_code == 400
    assert "intent_it" in r.get_json()["error"]


# TD2 — minimal draft (no scene, just intent) returns 200
def test_td2_draft_minimal_intent():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": "Aurora raised her blade against the shadow."}
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/draft", json={
                "intent_it": "Aurora alza la spada contro l'ombra",
            })
    assert r.status_code == 200
    data = r.get_json()
    assert "draft_text" in data
    assert len(data["draft_text"]) > 0
    assert data["model_used"] == "cerebras/zai-glm-4.7"


# TD3 — draft with scene_id loads scene context
def test_td3_draft_with_scene_context(tmp_path):
    scene_file = tmp_path / "scene_003.draft.yaml"
    scene_file.write_text(
        "scene_id: scene_003\n"
        "title: Kikyo Leaves the Shrine\n"
        "status: draft\n"
        "summary: Kikyo departs to grow abilities.\n"
        "participants:\n  - Kikyo\n  - Aurora\n",
        encoding="utf-8",
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": "Draft output with scene context."}
    mock_resp.raise_for_status = MagicMock()

    captured_prompt = {}

    def capture_post(url, json=None, **kw):
        captured_prompt["prompt"] = json.get("prompt", "") if json else ""
        return mock_resp

    with patch("requests.post", side_effect=capture_post), \
         patch("app.calliope_shell.server._SCENES_DIR", tmp_path):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/draft", json={
                "scene_id": "scene_003",
                "intent_it": "Kikyo medita nel bosco",
            })

    assert r.status_code == 200
    data = r.get_json()
    assert data["context_used"]["scene"] is True
    assert "Kikyo" in captured_prompt.get("prompt", "")


# TD4 — draft calls cerebras provider via llm_code endpoint
def test_td4_draft_uses_cerebras():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": "Literary output."}
    mock_resp.raise_for_status = MagicMock()

    captured_url = {}

    def capture_post(url, json=None, **kw):
        captured_url["url"] = url
        captured_url["provider"] = json.get("provider", "") if json else ""
        return mock_resp

    with patch("requests.post", side_effect=capture_post):
        app = _make_app()
        with app.test_client() as c:
            c.post("/api/draft", json={"intent_it": "test"})

    assert "/llm_code" in captured_url.get("url", "")
    assert captured_url.get("provider") == "cerebras"


# TD5 — gateway down returns 503
def test_td5_draft_gateway_down():
    import requests as _req
    with patch("requests.post", side_effect=_req.exceptions.ConnectionError("down")):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/draft", json={"intent_it": "test"})
    assert r.status_code == 503
    assert r.get_json()["code"] == "gateway_down"


# TD6 — char_focus narrows character loading
def test_td6_draft_char_focus(tmp_path):
    char_file = tmp_path / "aurora.draft.yaml"
    char_file.write_text(
        "name: Aurora\ntraits:\n  - compassionate\nrace: yokai\n"
        "speech_pattern:\n  vocabulary: poetic\n  pov: first_person\n",
        encoding="utf-8",
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": "Aurora spoke softly."}
    mock_resp.raise_for_status = MagicMock()

    captured = {}

    def capture_post(url, json=None, **kw):
        captured["prompt"] = json.get("prompt", "") if json else ""
        return mock_resp

    with patch("requests.post", side_effect=capture_post), \
         patch("app.calliope_shell.server._CHARS_DIR", tmp_path):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/draft", json={
                "intent_it": "Aurora parla con dolcezza",
                "char_focus": "Aurora",
            })

    assert r.status_code == 200
    data = r.get_json()
    assert data["context_used"]["char_sheets"] >= 1
    assert "Aurora" in captured.get("prompt", "")
    assert "compassionate" in captured.get("prompt", "")


# TD7 — audit_trail.log_event is called
def test_td7_draft_audit_trail():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": "Draft."}
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp), \
         patch("app.calliope_shell.audit_trail.log_event") as mock_audit:
        app = _make_app()
        with app.test_client() as c:
            c.post("/api/draft", json={"intent_it": "test audit"})

    mock_audit.assert_called_once()
    args = mock_audit.call_args
    assert args[0][0] == "draft.generate"


# TD8 — response includes lint_findings list
def test_td8_draft_includes_lint_findings():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": "Clean output."}
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/draft", json={"intent_it": "test"})

    data = r.get_json()
    assert "lint_findings" in data
    assert isinstance(data["lint_findings"], list)
