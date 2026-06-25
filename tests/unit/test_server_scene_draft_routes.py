"""Unit test per POST /api/scene/refine, /api/scene/variants, /api/draft, /api/summarize."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.calliope_shell.server import create_app

_SRV = "app.calliope_shell.server"
_SCRIPTS = str(Path(__file__).parents[2] / "scripts")


def _client():
    app, _ = create_app()
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def client():
    return _client()


@pytest.fixture(autouse=True)
def add_scripts_to_path():
    sys.path.insert(0, _SCRIPTS)
    yield
    if _SCRIPTS in sys.path:
        sys.path.remove(_SCRIPTS)


# ── POST /api/scene/refine ────────────────────────────────────────────────────

def test_refine_400_no_input(client):
    r = client.post("/api/scene/refine", json={})
    assert r.status_code == 400


def test_refine_400_no_feedback(client):
    r = client.post("/api/scene/refine", json={"scene_text": "old text"})
    assert r.status_code == 400


def test_refine_503_llm_error(client):
    with patch(f"{_SRV}.requests.post", side_effect=Exception("LLM unavailable")):
        r = client.post("/api/scene/refine", json={"scene_text": "text", "feedback": "fix it"})
    assert r.status_code == 503


def test_refine_200_success(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"result": "refined text here"}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp):
        r = client.post("/api/scene/refine", json={"scene_text": "original", "feedback": "shorter"})
    assert r.status_code == 200
    data = r.get_json()
    assert "refined_text" in data
    assert "diff" in data


def test_refine_uses_env_provider_model(client):
    """GATED-2: REFINE_PROVIDER/REFINE_MODEL env → passati al gateway."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"result": "abliterated output"}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp) as mock_post, \
         patch.dict("os.environ", {"REFINE_PROVIDER": "ollama", "REFINE_MODEL": "dolphin-mistral"}):
        r = client.post("/api/scene/refine", json={"scene_text": "original", "feedback": "dark"})
    assert r.status_code == 200
    call_body = mock_post.call_args[1]["json"]
    assert call_body["provider"] == "ollama"
    assert call_body["model"] == "dolphin-mistral"


# ── POST /api/scene/variants ──────────────────────────────────────────────────

def test_variants_400_no_prompt(client):
    r = client.post("/api/scene/variants", json={})
    assert r.status_code == 400


def test_variants_503_generation_error(client):
    with patch("generate_scene.generate_variants", side_effect=RuntimeError("gen failed")):
        r = client.post("/api/scene/variants", json={"prompt": "a battle"})
    assert r.status_code == 503


# ── POST /api/draft ───────────────────────────────────────────────────────────

def test_draft_400_no_intent(client):
    r = client.post("/api/draft", json={})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_draft_400_empty_intent(client):
    r = client.post("/api/draft", json={"intent_it": "   "})
    assert r.status_code == 400


# ── POST /api/summarize ───────────────────────────────────────────────────────

def test_summarize_400_no_text(client):
    r = client.post("/api/summarize", json={})
    assert r.status_code == 400


def test_summarize_503_connection_error(client):
    with patch(f"{_SRV}.requests.post", side_effect=requests.exceptions.ConnectionError):
        r = client.post("/api/summarize", json={"text": "some text to summarize"})
    assert r.status_code == 503


def test_summarize_200_success(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"result": '{"summary": "short", "key_facts": ["a", "b"]}'}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp):
        r = client.post("/api/summarize", json={"text": "long scene text here"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["summary"] == "short"
    assert data["key_facts"] == ["a", "b"]
    assert "word_count" in data


# ── POST /api/scene/blend ─────────────────────────────────────────────────────

def test_scene_blend_400_missing_variants_file(client):
    """Lines 831-832: variants_file_path mancante → 400."""
    r = client.post("/api/scene/blend", json={})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_scene_blend_400_path_traversal(client):
    """Lines 834-835: path fuori da /tmp o scenes/ → 400."""
    r = client.post("/api/scene/blend", json={"variants_file_path": "/etc/calliope_x.variants.md"})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_scene_blend_404_file_not_found(client):
    """Lines 836-837: path valido ma file inesistente → 404."""
    r = client.post("/api/scene/blend", json={
        "variants_file_path": "/tmp/calliope_nonexistent_test.variants.md",
    })
    assert r.status_code == 404
    assert "error" in r.get_json()


# ── Extra /api/summarize branches ────────────────────────────────────────────

def test_summarize_codeblock_json(client):
    """Line 1295: risposta LLM con JSON dentro code-block markdown."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "result": '```json\n{"summary": "short", "key_facts": ["x"]}\n```',
    }
    with patch(f"{_SRV}.requests.post", return_value=mock_resp):
        r = client.post("/api/summarize", json={"text": "some long text"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["summary"] == "short"


def test_summarize_non_json_result(client):
    """Lines 1299-1300: risposta LLM non JSON → summary = testo grezzo."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"result": "plain text, no JSON here"}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp):
        r = client.post("/api/summarize", json={"text": "text"})
    assert r.status_code == 200
    assert r.get_json()["summary"] == "plain text, no JSON here"


def test_summarize_generic_llm_exception(client):
    """Lines 1285-1287: eccezione generica nell'LLM call → 503."""
    with patch(f"{_SRV}.requests.post", side_effect=RuntimeError("oops")):
        r = client.post("/api/summarize", json={"text": "text"})
    assert r.status_code == 503


def test_summarize_audit_exception_silenced(client):
    """Lines 1310-1311: audit_trail.log_event lancia → silenziato."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"result": '{"summary": "s", "key_facts": []}'}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp), \
         patch("app.calliope_shell.audit_trail.log_event", side_effect=RuntimeError("db")):
        r = client.post("/api/summarize", json={"text": "text"})
    assert r.status_code == 200


# ── POST /api/draft — success + error branches ────────────────────────────────

def test_draft_200_success(client):
    """Lines 1093-1247: draft_scene success path senza scene_id."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"result": "The forest trembled with dread."}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp), \
         patch(f"{_SRV}._search_lore", return_value=[]):
        r = client.post("/api/draft", json={"intent_it": "Una scena nel bosco oscuro"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["draft_text"] == "The forest trembled with dread."
    assert "model_used" in data
    assert "context_used" in data


def test_draft_503_connection_error(client):
    """Line 1192: ConnectionError → 503 gateway_down."""
    with patch(f"{_SRV}.requests.post",
               side_effect=requests.exceptions.ConnectionError("refused")):
        r = client.post("/api/draft", json={"intent_it": "Una battaglia"})
    assert r.status_code == 503
    assert r.get_json().get("code") == "gateway_down"


def test_draft_503_generic_exception(client):
    """Lines 1193-1195: generic exception → 503."""
    with patch(f"{_SRV}.requests.post", side_effect=RuntimeError("oops")):
        r = client.post("/api/draft", json={"intent_it": "Una battaglia"})
    assert r.status_code == 503
    assert "error" in r.get_json()


def test_draft_200_with_scene_id(client, tmp_path):
    """Lines 1097-1113: draft con scene_id → carica partecipanti da YAML fallback."""
    import yaml

    scene_yaml = {
        "scene_id": "draft-test",
        "title": "Test Scene",
        "summary": "Una scena di prova.",
        "participants": ["Aurora"],
    }
    (tmp_path / "draft-test.yaml").write_text(yaml.dump(scene_yaml), encoding="utf-8")

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"result": "The hero arrives."}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp), \
         patch(f"{_SRV}._search_lore", return_value=[]), \
         patch(f"{_SRV}._SCENES_DIR", tmp_path), \
         patch("app.db.get_db", side_effect=Exception("no db")):
        r = client.post("/api/draft", json={
            "intent_it": "Aurora entra nella scena",
            "scene_id": "draft-test",
        })
    assert r.status_code == 200
    assert r.get_json()["draft_text"] == "The hero arrives."


# ── POST /api/scene/variants — success path ───────────────────────────────────

# ── POST /api/scene/refine — scene_file_path + auto_lint branches ─────────────

def test_refine_scene_file_path_outside_scenes_dir_400(client):
    """Lines 674-675: scene_file_path fuori da _SCENES_DIR → ValueError → 400."""
    r = client.post("/api/scene/refine", json={
        "scene_file_path": "/etc/passwd",
        "feedback": "shorten it",
    })
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_refine_scene_file_path_not_found_400(client, tmp_path):
    """Lines 676-677: path valido ma file inesistente → Exception → 400."""
    with patch(f"{_SRV}._SCENES_DIR", tmp_path):
        r = client.post("/api/scene/refine", json={
            "scene_file_path": str(tmp_path / "nonexistent.md"),
            "feedback": "shorten it",
        })
    assert r.status_code == 400
    assert "Cannot read file" in r.get_json().get("error", "")


def test_refine_auto_lint_success(client):
    """Line 712: auto_lint=True e style_filter riesce → lint_findings in response."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"result": "refined text here"}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp), \
         patch("style_filter.filter_response",
               return_value=("refined text here", [{"pattern": "foo", "action": "stripped"}])):
        r = client.post("/api/scene/refine", json={
            "scene_text": "original text",
            "feedback": "shorter",
            "auto_lint": True,
        })
    assert r.status_code == 200
    assert r.get_json()["auto_lint_applied"] is True


def test_refine_auto_lint_exception_silenced(client):
    """Lines 707-714: auto_lint=True, style_filter lancia → non-fatal, 200."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"result": "refined text here"}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp), \
         patch("style_filter.filter_response", side_effect=ImportError("no filter")):
        r = client.post("/api/scene/refine", json={
            "scene_text": "original text",
            "feedback": "shorter",
            "auto_lint": True,
        })
    assert r.status_code == 200


def test_refine_audit_exception_silenced(client):
    """Lines 730-731: audit_trail.log_event lancia in refine → except pass."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"result": "refined"}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp), \
         patch("app.calliope_shell.audit_trail.log_event", side_effect=RuntimeError("db")):
        r = client.post("/api/scene/refine", json={
            "scene_text": "original",
            "feedback": "fix it",
        })
    assert r.status_code == 200


# ── POST /api/scene/variants — load_config + route_scene exception branches ───

def test_variants_load_config_exception_uses_default(client):
    """Lines 758-759: load_config lancia → config = DEFAULT_CONFIG, continua."""
    mock_variants = [{"style": "default", "text": "A battle.", "latency_ms": 80}]
    with patch("route_scene.load_config", side_effect=Exception("yaml missing")), \
         patch("generate_scene.generate_variants", return_value=mock_variants), \
         patch("generate_scene._write_variants_file"):
        r = client.post("/api/scene/variants", json={"prompt": "a battle"})
    assert r.status_code == 200


def test_variants_route_scene_exception_uses_default(client):
    """Lines 767-770: route_scene lancia → tier e provider di default."""
    mock_variants = [{"style": "default", "text": "A battle.", "latency_ms": 80}]
    with patch("route_scene.route_scene", side_effect=RuntimeError("config error")), \
         patch("generate_scene.generate_variants", return_value=mock_variants), \
         patch("generate_scene._write_variants_file"):
        r = client.post("/api/scene/variants", json={"prompt": "a battle"})
    assert r.status_code == 200


def test_variants_200_success(client):
    """Lines 788-816: generate_variants succeed → file scritto, 200 con variants."""
    mock_variants = [
        {"style": "dramatic", "text": "The sword clashed.", "latency_ms": 100},
        {"style": "lyrical", "text": "Like stars colliding.", "latency_ms": 120},
    ]
    mock_write = MagicMock()
    with patch("generate_scene.generate_variants", return_value=mock_variants), \
         patch("generate_scene._write_variants_file", mock_write):
        r = client.post("/api/scene/variants", json={"prompt": "a duel at dawn"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["n"] == 2
    assert len(data["variants"]) == 2
    assert "variants_file_path" in data
    mock_write.assert_called_once()


def test_variants_audit_exception_silenced(client):
    """Lines 806-807: audit_trail.log_event lancia → except pass."""
    mock_variants = [{"style": "dramatic", "text": "clash.", "latency_ms": 50}]
    with patch("generate_scene.generate_variants", return_value=mock_variants), \
         patch("generate_scene._write_variants_file"), \
         patch("app.calliope_shell.audit_trail.log_event",
               side_effect=RuntimeError("db")):
        r = client.post("/api/scene/variants", json={"prompt": "a duel"})
    assert r.status_code == 200


def test_draft_parse_scene_yaml_bad_yaml(client, tmp_path):
    """Lines 974-976: _parse_scene_yaml su YAML corrotto → except → return {}.

    resolve_scene_context viene patchata per evitare che il YAML corrotto
    venga parsato da quel path (che non ha try/except).
    """
    bad_yaml = tmp_path / "bad-scene.yaml"
    bad_yaml.write_text(":\ninvalid: yaml: [unclosed", encoding="utf-8")

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"result": "A dark scene."}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp), \
         patch(f"{_SRV}._search_lore", return_value=[]), \
         patch(f"{_SRV}._SCENES_DIR", tmp_path), \
         patch("app.db.get_db", side_effect=Exception("no db")), \
         patch(f"{_SRV}.resolve_scene_context", return_value=""):
        r = client.post("/api/draft", json={
            "intent_it": "Una scena oscura",
            "scene_id": "bad-scene",
        })
    assert r.status_code == 200


def test_draft_parse_scene_yaml_non_dict(client, tmp_path):
    """Line 960: _parse_scene_yaml con YAML che produce lista → not isinstance(raw, dict) → {}."""
    list_yaml = tmp_path / "list-scene.yaml"
    list_yaml.write_text("- item1\n- item2\n", encoding="utf-8")

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"result": "The scene continues."}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp), \
         patch(f"{_SRV}._search_lore", return_value=[]), \
         patch(f"{_SRV}._SCENES_DIR", tmp_path), \
         patch("app.db.get_db", side_effect=Exception("no db")), \
         patch(f"{_SRV}.resolve_scene_context", return_value=""):
        r = client.post("/api/draft", json={
            "intent_it": "La scena continua",
            "scene_id": "list-scene",
        })
    assert r.status_code == 200


def test_draft_audit_exception_silenced(client):
    """Lines 1233-1234: audit_trail.log_event lancia in draft → except pass."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"result": "draft text"}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp), \
         patch(f"{_SRV}._search_lore", return_value=[]), \
         patch("app.calliope_shell.audit_trail.log_event", side_effect=RuntimeError("db")):
        r = client.post("/api/draft", json={"intent_it": "Una scena"})
    assert r.status_code == 200


def test_draft_with_char_focus_exceptions_silenced(client):
    """Lines 1123, 1130-1131, 1136-1137: char_focus + memory/grounding exceptions."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"result": "draft"}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp), \
         patch(f"{_SRV}._search_lore", return_value=[]), \
         patch("app.calliope_shell.char_memory.retrieve_multi_signal",
               side_effect=RuntimeError("db")), \
         patch("app.calliope_shell.char_grounding.retrieve_char_grounding",
               side_effect=RuntimeError("grounding")):
        r = client.post("/api/draft", json={
            "intent_it": "Aurora combatte nel bosco",
            "char_focus": "Aurora",
        })
    assert r.status_code == 200


def test_draft_with_style_hints(client):
    """Line 1166: style_hints presente → aggiunto ai prompt_parts."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"result": "styled draft"}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp), \
         patch(f"{_SRV}._search_lore", return_value=[]):
        r = client.post("/api/draft", json={
            "intent_it": "Una scena gotica",
            "style_hints": "gothic tone, vivid sensory details",
        })
    assert r.status_code == 200
    assert r.get_json()["context_used"]["style_hints"] is True


def test_draft_persist_db_fail_silenced(client):
    """Lines 1198-1206: persist=True + scene_id, DB fail → warning, 200."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"result": "draft text"}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp), \
         patch(f"{_SRV}._search_lore", return_value=[]), \
         patch(f"{_SRV}.resolve_scene_context", return_value=""), \
         patch("app.db.get_db", side_effect=Exception("no db")):
        r = client.post("/api/draft", json={
            "intent_it": "Una scena",
            "persist": True,
            "scene_id": "test-persist",
        })
    assert r.status_code == 200


def test_draft_style_filter_exception_silenced(client):
    """Lines 1215-1216: style_filter lancia nel draft → non-fatal, 200."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"result": "draft text"}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp), \
         patch(f"{_SRV}._search_lore", return_value=[]), \
         patch("style_filter.filter_response", side_effect=RuntimeError("filter broken")):
        r = client.post("/api/draft", json={"intent_it": "Una scena"})
    assert r.status_code == 200


def test_draft_persist_success(client):
    """Lines 1202-1204: persist=True + scene_id + DB OK → commit+close chiamati."""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = None  # no char found

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"result": "draft text"}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp), \
         patch(f"{_SRV}._search_lore", return_value=[]), \
         patch(f"{_SRV}.resolve_scene_context", return_value=""), \
         patch("app.db.get_db", return_value=mock_conn), \
         patch("app.db.messages.add_message"):
        r = client.post("/api/draft", json={
            "intent_it": "Una scena",
            "persist": True,
            "scene_id": "test-persist",
        })
    assert r.status_code == 200
    mock_conn.commit.assert_called()


def test_draft_empty_participant_skipped(client, tmp_path):
    """Line 1123: participants con stringa vuota → 'if not cn: continue'."""
    import yaml

    scene_yaml = {
        "scene_id": "empty-part",
        "title": "Test",
        "summary": "test",
        "participants": ["Aurora", ""],
    }
    (tmp_path / "empty-part.yaml").write_text(yaml.dump(scene_yaml), encoding="utf-8")

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"result": "draft"}
    with patch(f"{_SRV}.requests.post", return_value=mock_resp), \
         patch(f"{_SRV}._search_lore", return_value=[]), \
         patch(f"{_SRV}._SCENES_DIR", tmp_path), \
         patch(f"{_SRV}.resolve_scene_context", return_value=""), \
         patch("app.db.get_db", side_effect=Exception("no db")):
        r = client.post("/api/draft", json={
            "intent_it": "Una scena",
            "scene_id": "empty-part",
        })
    assert r.status_code == 200


# ── POST /api/scene/blend — success path ─────────────────────────────────────

def test_scene_blend_200_success(client):
    """Lines 840-874: blend success — parse, blend, write, audit, 200."""
    import tempfile

    vf = Path(tempfile.mktemp(suffix=".variants.md", prefix="calliope_"))
    vf.write_text("# placeholder variants content", encoding="utf-8")

    mock_variants = [
        {"style": "dramatic", "text": "Swords clash.", "latency_ms": 80},
        {"style": "lyrical", "text": "Steel sings.", "latency_ms": 90},
    ]
    try:
        with patch("blend_scene.parse_variants_file", return_value=mock_variants), \
             patch("blend_scene.blend_variants", return_value=("Blended output.", 120)), \
             patch("blend_scene.write_blended_output"):
            r = client.post("/api/scene/blend", json={
                "variants_file_path": str(vf),
                "blend_indices": [1, 2],
            })
    finally:
        vf.unlink(missing_ok=True)

    assert r.status_code == 200
    data = r.get_json()
    assert data["blended_text"] == "Blended output."
    assert "output_path" in data
    assert data["latency_ms"] == 120


def test_scene_blend_400_no_variants_parsed(client):
    """Line 844: parse_variants_file ritorna [] → 400 no variants parsed."""
    import tempfile

    vf = Path(tempfile.mktemp(suffix=".variants.md", prefix="calliope_"))
    vf.write_text("# empty file", encoding="utf-8")
    try:
        with patch("blend_scene.parse_variants_file", return_value=[]):
            r = client.post("/api/scene/blend", json={"variants_file_path": str(vf)})
    finally:
        vf.unlink(missing_ok=True)
    assert r.status_code == 400
    assert "no variants" in r.get_json()["error"]


def test_scene_blend_200_string_indices(client):
    """Line 847: blend_indices come stringa → parse_blend_spec."""
    import tempfile

    vf = Path(tempfile.mktemp(suffix=".variants.md", prefix="calliope_"))
    vf.write_text("# content", encoding="utf-8")
    mock_variants = [{"style": "d", "text": "Clash.", "latency_ms": 50}]
    try:
        with patch("blend_scene.parse_variants_file", return_value=mock_variants), \
             patch("blend_scene.parse_blend_spec", return_value=[1]), \
             patch("blend_scene.blend_variants", return_value=("blended", 80)), \
             patch("blend_scene.write_blended_output"):
            r = client.post("/api/scene/blend", json={
                "variants_file_path": str(vf),
                "blend_indices": "1",
            })
    finally:
        vf.unlink(missing_ok=True)
    assert r.status_code == 200


def test_scene_blend_503_blend_exception(client):
    """Lines 854-856: blend_variants lancia → 503."""
    import tempfile

    vf = Path(tempfile.mktemp(suffix=".variants.md", prefix="calliope_"))
    vf.write_text("# content", encoding="utf-8")
    mock_variants = [{"style": "d", "text": "Clash.", "latency_ms": 50}]
    try:
        with patch("blend_scene.parse_variants_file", return_value=mock_variants), \
             patch("blend_scene.blend_variants", side_effect=RuntimeError("blend failed")):
            r = client.post("/api/scene/blend", json={"variants_file_path": str(vf)})
    finally:
        vf.unlink(missing_ok=True)
    assert r.status_code == 503
    assert "error" in r.get_json()


def test_scene_blend_audit_exception_silenced(client):
    """Lines 871-872: blend audit lancia → silenced, 200."""
    import tempfile

    vf = Path(tempfile.mktemp(suffix=".variants.md", prefix="calliope_"))
    vf.write_text("# placeholder", encoding="utf-8")
    mock_variants = [{"style": "d", "text": "Text.", "latency_ms": 50}]
    try:
        with patch("blend_scene.parse_variants_file", return_value=mock_variants), \
             patch("blend_scene.blend_variants", return_value=("Blended.", 60)), \
             patch("blend_scene.write_blended_output"), \
             patch("app.calliope_shell.audit_trail.log_event", side_effect=RuntimeError("db")):
            r = client.post("/api/scene/blend", json={
                "variants_file_path": str(vf),
                "blend_indices": [1],
            })
    finally:
        vf.unlink(missing_ok=True)

    assert r.status_code == 200
