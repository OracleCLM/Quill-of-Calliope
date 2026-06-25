"""
Test per POST /api/lore/search (server.py) non ancora coperto:
  - 400 se query assente
  - 200 + error se ChromaDB fallisce (exception non-fatal)
  - 200 + hits su query valida

E per POST /api/scene/revive (minimal cases non-LLM):
  - 400 se scene_id assente
  - 404 se nessuna YAML scene corrisponde
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock

from app.calliope_shell.server import create_app

_SRV = "app.calliope_shell.server"


def _client():
    app, _ = create_app()
    app.config["TESTING"] = True
    return app.test_client()


# ── POST /api/lore/search ─────────────────────────────────────────────────────

def test_lore_search_missing_query_400():
    with _client() as c:
        r = c.post("/api/lore/search", json={})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_lore_search_chromadb_fail_returns_empty():
    """ChromaDB solleva eccezione → 200 con results=[], count=0, error str."""
    with _client() as c:
        with patch(f"{_SRV}._chroma_client", side_effect=Exception("chroma down")):
            r = c.post("/api/lore/search", json={"query": "drago"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["results"] == []
    assert data["count"] == 0
    assert "error" in data


def test_lore_search_success_returns_hits():
    mock_chroma = MagicMock()
    col = MagicMock()
    col.query.return_value = {
        "documents": [["Il Drago delle Cime abita a nord."]],
        "metadatas": [[{"source": "lore/draghi.md", "type": "lore", "char": ""}]],
        "distances": [[0.12]],
    }
    mock_chroma.get_collection.return_value = col

    with _client() as c:
        with patch(f"{_SRV}._chroma_client", return_value=mock_chroma):
            with patch(f"{_SRV}.audit_trail" if False else "builtins.print"):
                r = c.post("/api/lore/search", json={"query": "drago"})

    assert r.status_code == 200
    data = r.get_json()
    assert data["count"] == 1
    assert data["query"] == "drago"
    hit = data["results"][0]
    assert "drago" in hit["text"].lower() or "Drago" in hit["text"]
    assert hit["source"] == "lore/draghi.md"


def test_lore_search_n_capped_at_20():
    """n>20 viene silenziosamente cappato a 20 (no error)."""
    mock_chroma = MagicMock()
    col = MagicMock()
    col.query.return_value = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    mock_chroma.get_collection.return_value = col

    with _client() as c:
        with patch(f"{_SRV}._chroma_client", return_value=mock_chroma):
            r = c.post("/api/lore/search", json={"query": "qualcosa", "n": 100})

    assert r.status_code == 200
    col.query.assert_called_once()
    _, call_kwargs = col.query.call_args
    assert call_kwargs.get("n_results", 0) == 20


# ── POST /api/scene/revive ────────────────────────────────────────────────────

def test_scene_revive_missing_scene_id_400():
    with _client() as c:
        r = c.post("/api/scene/revive", json={})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_scene_revive_scene_not_found_404(tmp_path):
    """_SCENES_DIR punta a tmp_path vuota → nessun match → 404."""
    with _client() as c:
        with patch(f"{_SRV}._SCENES_DIR", tmp_path):
            r = c.post("/api/scene/revive", json={"scene_id": "nonexistent-scene"})
    assert r.status_code == 404
    assert "error" in r.get_json()


def test_scene_revive_success_full_mock(tmp_path):
    """Lines 35-84 (_load_char_sheets), 1349-1418 (revive success path).

    Copre: char_facts (retrieve_multi_signal), recent_messages (chroma),
    operator_notes branch, LLM call success e audit hook.
    """
    import yaml

    # Scene YAML con tutti i campi opzionali compilati
    scene_yaml = {
        "scene_id": "test-revival",
        "title": "La Battaglia del Bosco",
        "summary": "Aurora e Marcus si confrontano nel bosco oscuro.",
        "participants": ["Aurora", "Marcus"],
        "last_msg_excerpt": "La spada brilla sotto la luna.",
        "status": "dormant",
        "operator_notes": "Riprendere dalla scena del duello.",
    }
    scene_file = tmp_path / "test-revival.yaml"
    scene_file.write_text(yaml.dump(scene_yaml), encoding="utf-8")

    # Mock retrieve_multi_signal → ritorna fatti personaggio
    mock_char_facts = [{"fact_text": "è coraggiosa"}, {"fact_text": "usa la spada"}]

    # Mock ChromaDB → ritorna messaggi recenti
    mock_chroma = MagicMock()
    col_mock = MagicMock()
    col_mock.query.return_value = {"documents": [["Un messaggio recente."]]}
    mock_chroma.get_collection.return_value = col_mock

    # Mock LLM → risposta revival summary
    mock_llm_resp = MagicMock()
    mock_llm_resp.raise_for_status.return_value = None
    mock_llm_resp.json.return_value = {"result": "Il bosco era tranquillo quando..."}

    with _client() as c:
        with patch(f"{_SRV}._SCENES_DIR", tmp_path), \
             patch("app.calliope_shell.char_memory.retrieve_multi_signal",
                   return_value=mock_char_facts), \
             patch(f"{_SRV}._chroma_client", return_value=mock_chroma), \
             patch(f"{_SRV}._search_lore", return_value=["Lore snippet"]), \
             patch(f"{_SRV}.requests.post", return_value=mock_llm_resp):
            r = c.post("/api/scene/revive", json={"scene_id": "test-revival"})

    assert r.status_code == 200
    data = r.get_json()
    assert "scene_context" in data
    assert data["scene_context"]["scene_id"] == "test-revival"
    assert "suggested_reentry" in data
    assert data["suggested_reentry"] != ""


def test_scene_revive_char_memory_fails_silently(tmp_path):
    """Lines 1349-1350: retrieve_multi_signal lancia → silenziata."""
    import yaml

    scene_yaml = {
        "scene_id": "test-fail",
        "title": "Test",
        "summary": "test summary",
        "participants": ["Zeta"],
    }
    (tmp_path / "test-fail.yaml").write_text(yaml.dump(scene_yaml), encoding="utf-8")

    mock_llm_resp = MagicMock()
    mock_llm_resp.raise_for_status.return_value = None
    mock_llm_resp.json.return_value = {"result": "revival text"}

    with _client() as c:
        with patch(f"{_SRV}._SCENES_DIR", tmp_path), \
             patch("app.calliope_shell.char_memory.retrieve_multi_signal",
                   side_effect=RuntimeError("DB busy")), \
             patch(f"{_SRV}._chroma_client", side_effect=Exception("chroma down")), \
             patch(f"{_SRV}._search_lore", return_value=[]), \
             patch(f"{_SRV}.requests.post", return_value=mock_llm_resp):
            r = c.post("/api/scene/revive", json={"scene_id": "test-fail"})

    assert r.status_code == 200


def test_scene_revive_audit_exception_silenced(tmp_path):
    """Lines 1417-1418: audit_trail.log_event nel revive lancia → silenced, 200."""
    import yaml

    scene_yaml = {
        "scene_id": "revive-audit",
        "title": "Test",
        "summary": "summary",
        "participants": ["Zeta"],
    }
    (tmp_path / "revive-audit.yaml").write_text(yaml.dump(scene_yaml), encoding="utf-8")

    mock_llm_resp = MagicMock()
    mock_llm_resp.raise_for_status.return_value = None
    mock_llm_resp.json.return_value = {"result": "revival text"}

    with _client() as c:
        with patch(f"{_SRV}._SCENES_DIR", tmp_path), \
             patch("app.calliope_shell.char_memory.retrieve_multi_signal",
                   side_effect=RuntimeError("DB")), \
             patch(f"{_SRV}._chroma_client", side_effect=Exception("down")), \
             patch(f"{_SRV}._search_lore", return_value=[]), \
             patch(f"{_SRV}.requests.post", return_value=mock_llm_resp), \
             patch("app.calliope_shell.audit_trail.log_event",
                   side_effect=RuntimeError("db")):
            r = c.post("/api/scene/revive", json={"scene_id": "revive-audit"})

    assert r.status_code == 200


def test_load_char_sheets_bad_json_in_db():
    """Lines 52-53: DB row con card_json invalido → except pass, char aggiunto con card={}."""
    import app.calliope_shell.server as srv

    mock_conn = MagicMock()
    mock_row = MagicMock()
    # row["card_json"] → MagicMock (truthy) → json.loads(MagicMock()) raises TypeError
    mock_conn.execute.return_value.fetchone.return_value = mock_row

    with patch("app.db.get_db", return_value=mock_conn):
        result = srv._load_char_sheets(["Aurora"])

    # Anche con JSON invalido, il personaggio viene aggiunto con card={}
    assert isinstance(result, list)
    assert len(result) == 1


def test_load_char_sheets_yaml_read_exception():
    """Lines 81-82: DB fail → fallback YAML, yaml.safe_load lancia → except pass → [].

    Usa 'aurora' (corrisponde ad aurora.draft.yaml) ma fa fallire safe_load.
    """
    import yaml
    import app.calliope_shell.server as srv

    with patch("app.db.get_db", side_effect=RuntimeError("no db")), \
         patch("yaml.safe_load", side_effect=yaml.YAMLError("corrupt")):
        result = srv._load_char_sheets(["aurora"])

    assert result == []


def test_load_char_sheets_db_fallback_to_yaml(tmp_path):
    """Lines 63-64, 70-83: get_db lancia → except pass → YAML fallback caricato.

    Si usa 'aurora' come partecipante perché aurora.draft.yaml esiste in characters/.
    Patchando get_db a fallire, _load_char_sheets bypassa il DB e legge il YAML.
    """
    import yaml

    scene_yaml = {
        "scene_id": "test-yaml-fallback",
        "title": "Test YAML Fallback",
        "summary": "test",
        "participants": ["Aurora"],
    }
    (tmp_path / "test-yaml-fallback.yaml").write_text(yaml.dump(scene_yaml), encoding="utf-8")

    mock_llm_resp = MagicMock()
    mock_llm_resp.raise_for_status.return_value = None
    mock_llm_resp.json.return_value = {"result": "revival summary"}

    with _client() as c:
        with patch(f"{_SRV}._SCENES_DIR", tmp_path), \
             patch("app.db.get_db", side_effect=RuntimeError("DB unavailable")), \
             patch(f"{_SRV}._chroma_client", side_effect=Exception("chroma down")), \
             patch("app.calliope_shell.char_memory.retrieve_multi_signal",
                   side_effect=RuntimeError("DB")), \
             patch(f"{_SRV}._search_lore", return_value=[]), \
             patch(f"{_SRV}.requests.post", return_value=mock_llm_resp):
            r = c.post("/api/scene/revive", json={"scene_id": "test-yaml-fallback"})

    assert r.status_code == 200


# ── POST /api/lore/check ─────────────────────────────────────────────────────

def test_lore_check_missing_text_400():
    with _client() as c:
        r = c.post("/api/lore/check", json={})
    assert r.status_code == 400
    assert r.get_json()["error"] == "text is required"


def test_lore_check_no_lore_returns_coherent_true():
    """Nessun snippet lore trovato → coherent=True, issues=[]."""
    with _client() as c:
        with patch(f"{_SRV}._search_lore", return_value=[]):
            r = c.post("/api/lore/check", json={"text": "The dragon flew high."})
    assert r.status_code == 200
    data = r.get_json()
    assert data["coherent"] is True
    assert data["issues"] == []


def test_lore_check_with_lore_llm_success():
    """LLM risponde JSON valido con coherent+issues → 200."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"result": '{"coherent": true, "issues": []}'}

    with _client() as c:
        with patch(f"{_SRV}._search_lore", return_value=["lore snippet"]):
            with patch(f"{_SRV}.requests.post", return_value=mock_resp):
                r = c.post("/api/lore/check", json={"text": "The dragon flew high."})
    assert r.status_code == 200
    data = r.get_json()
    assert "coherent" in data or "error" in data  # degrada se JSON mal formato


def test_lore_check_chromadb_fail_silent():
    """Lines 93-94: _search_lore lancia su ChromaDB → silently [] → coherent=True."""
    with _client() as c:
        with patch(f"{_SRV}._chroma_client", side_effect=Exception("chroma down")):
            r = c.post("/api/lore/check", json={"text": "The dragon flew high."})
    assert r.status_code == 200
    assert r.get_json()["coherent"] is True


def test_lore_search_audit_exception_silenced(tmp_path):
    """Lines 1480-1481: lore_search ha risultati ma audit lancia → silenced, 200."""
    mock_chroma = MagicMock()
    col = MagicMock()
    col.query.return_value = {
        "documents": [["Il Drago abita a nord."]],
        "metadatas": [[{"source": "lore/draghi.md", "type": "lore", "char": ""}]],
        "distances": [[0.1]],
    }
    mock_chroma.get_collection.return_value = col

    with _client() as c:
        with patch(f"{_SRV}._chroma_client", return_value=mock_chroma), \
             patch("app.calliope_shell.audit_trail.log_event", side_effect=RuntimeError("db")):
            r = c.post("/api/lore/search", json={"query": "drago"})
    assert r.status_code == 200
    assert r.get_json()["count"] == 1


def test_lore_check_with_scene_id(tmp_path):
    """Lines 1498-1503: lore_check con scene_id → search_query arricchita."""
    import yaml

    scene_yaml = {"scene_id": "lore-test", "title": "La Caverna del Drago", "summary": "test"}
    (tmp_path / "lore-test.yaml").write_text(yaml.dump(scene_yaml), encoding="utf-8")

    with _client() as c:
        with patch(f"{_SRV}._SCENES_DIR", tmp_path), \
             patch(f"{_SRV}._search_lore", return_value=[]):
            r = c.post("/api/lore/check", json={
                "text": "The dragon flies.",
                "scene_id": "lore-test",
            })
    assert r.status_code == 200
    assert r.get_json()["coherent"] is True


def test_lore_check_no_lore_audit_except():
    """Lines 1514-1515: no lore, audit_trail lancia → silenced, 200 coherent=True."""
    with _client() as c:
        with patch(f"{_SRV}._search_lore", return_value=[]), \
             patch("app.calliope_shell.audit_trail.log_event", side_effect=RuntimeError("db")):
            r = c.post("/api/lore/check", json={"text": "Some text."})
    assert r.status_code == 200
    assert r.get_json()["coherent"] is True


def test_lore_check_llm_connection_error():
    """Lines 1549-1550: lore_check LLM ConnectionError → 503 gateway_down."""
    import requests as req_module

    with _client() as c:
        with patch(f"{_SRV}._search_lore", return_value=["lore snippet"]), \
             patch(f"{_SRV}.requests.post",
                   side_effect=req_module.exceptions.ConnectionError("refused")):
            r = c.post("/api/lore/check", json={"text": "Some text."})
    assert r.status_code == 503
    assert r.get_json().get("code") == "gateway_down"


def test_lore_check_llm_generic_exception():
    """Lines 1551-1553: lore_check LLM generic exception → 503."""
    with _client() as c:
        with patch(f"{_SRV}._search_lore", return_value=["lore snippet"]), \
             patch(f"{_SRV}.requests.post", side_effect=RuntimeError("oops")):
            r = c.post("/api/lore/check", json={"text": "Some text."})
    assert r.status_code == 503
    assert "error" in r.get_json()


def test_lore_check_llm_json_parse_error():
    """Lines 1565-1567: LLM risponde testo non-JSON → issues=[warning], coherent=False."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"result": "NOT VALID JSON {broken"}

    with _client() as c:
        with patch(f"{_SRV}._search_lore", return_value=["lore snippet"]), \
             patch(f"{_SRV}.requests.post", return_value=mock_resp):
            r = c.post("/api/lore/check", json={"text": "Some text."})
    assert r.status_code == 200
    data = r.get_json()
    assert data["coherent"] is False
    assert len(data["issues"]) > 0


def test_lore_check_llm_codeblock_json():
    """Line 1561: LLM risponde JSON in code block → strip → parsed."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "result": '```json\n{"coherent": true, "issues": []}\n```',
    }

    with _client() as c:
        with patch(f"{_SRV}._search_lore", return_value=["lore snippet"]), \
             patch(f"{_SRV}.requests.post", return_value=mock_resp):
            r = c.post("/api/lore/check", json={"text": "Some text."})
    assert r.status_code == 200
    assert r.get_json()["coherent"] is True


def test_lore_check_audit_exception_silenced():
    """Lines 1577-1578: lore_check audit lancia → silenced, 200."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"result": '{"coherent": true, "issues": []}'}

    with _client() as c:
        with patch(f"{_SRV}._search_lore", return_value=["lore snippet"]), \
             patch(f"{_SRV}.requests.post", return_value=mock_resp), \
             patch("app.calliope_shell.audit_trail.log_event", side_effect=RuntimeError("db")):
            r = c.post("/api/lore/check", json={"text": "Some text."})
    assert r.status_code == 200


# ── POST /api/scene/revive — DB fallback (GATED-4 fix) ───────────────────────

def test_scene_revive_db_fallback_200(tmp_path):
    """YAML dir vuota → DB fallback → 200 con scene da DB."""
    from app.db import get_db, init_schema, new_id
    from app.db.messages import add_message

    db_path = tmp_path / "revive.db"
    conn = get_db(db_path)
    init_schema(conn)
    scene_id = new_id()
    conn.execute("INSERT INTO scenes (id, title, location) VALUES (?, ?, ?)",
                 (scene_id, "Scena DB Test", "Bosco"))
    conn.commit()
    add_message(conn, scene_id=scene_id, author_name="Alice",
                content_original="msg1", position_order=0)
    conn.close()

    mock_llm = MagicMock()
    mock_llm.raise_for_status.return_value = None
    mock_llm.json.return_value = {"result": "Revival text from DB scene."}

    import os
    with _client() as c:
        with patch(f"{_SRV}._SCENES_DIR", tmp_path), \
             patch("app.db.CALLIOPE_DB_PATH", db_path), \
             patch.dict(os.environ, {"CALLIOPE_DB_PATH": str(db_path)}), \
             patch(f"{_SRV}._chroma_client", side_effect=Exception("down")), \
             patch(f"{_SRV}._search_lore", return_value=[]), \
             patch(f"{_SRV}.requests.post", return_value=mock_llm):
            r = c.post("/api/scene/revive", json={"scene_id": scene_id})
    assert r.status_code == 200
    data = r.get_json()
    assert "suggested_reentry" in data
    assert data["scene_context"]["scene_id"] == scene_id
