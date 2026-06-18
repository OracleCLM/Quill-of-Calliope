"""GAP-30: test contratto route /api/char/memory_append|replace|recall + /api/char/<name>/facts."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def _make_app():
    from app.calliope_shell.server import create_app
    app, _ = create_app()
    app.config["TESTING"] = True
    return app


# --- /api/char/memory_append ------------------------------------------------


def test_memory_append_missing_char_returns_400():
    app = _make_app()
    with app.test_client() as c:
        r = c.post("/api/char/memory_append", json={"fact": "ha un cicatrice"})
    assert r.status_code == 400
    assert "char" in r.get_json()["error"]


def test_memory_append_missing_fact_returns_400():
    app = _make_app()
    with app.test_client() as c:
        r = c.post("/api/char/memory_append", json={"char": "Aria"})
    assert r.status_code == 400


def test_memory_append_success_returns_200():
    with patch("app.calliope_shell.server.char_memory_append",
               return_value={"success": True, "fact": "ha un cicatrice"}):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/char/memory_append", json={"char": "Aria", "fact": "ha un cicatrice"})
    assert r.status_code == 200


def test_memory_append_failure_returns_400():
    with patch("app.calliope_shell.server.char_memory_append",
               return_value={"success": False, "error": "duplicato"}):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/char/memory_append", json={"char": "Aria", "fact": "x"})
    assert r.status_code == 400


# --- /api/char/memory_replace -----------------------------------------------


def test_memory_replace_missing_fields_returns_400():
    app = _make_app()
    with app.test_client() as c:
        r = c.post("/api/char/memory_replace", json={"char": "Aria", "old_fact": "vecchio"})
    assert r.status_code == 400
    assert "new_fact" in r.get_json()["error"]


def test_memory_replace_requires_approval_returns_202():
    with patch("app.calliope_shell.server.char_memory_replace",
               return_value={"requires_approval": True, "candidates": ["candidato"]}):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/char/memory_replace", json={
                "char": "Aria", "old_fact": "vecchio", "new_fact": "nuovo"
            })
    assert r.status_code == 202


def test_memory_replace_approved_returns_200():
    with patch("app.calliope_shell.server.char_memory_replace",
               return_value={"success": True}):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/char/memory_replace", json={
                "char": "Aria", "old_fact": "vecchio", "new_fact": "nuovo", "approved": True
            })
    assert r.status_code == 200


# --- /api/char/recall --------------------------------------------------------


def test_char_recall_missing_char_returns_400():
    app = _make_app()
    with app.test_client() as c:
        r = c.post("/api/char/recall", json={"query": "battaglia"})
    assert r.status_code == 400


def test_char_recall_missing_query_returns_400():
    app = _make_app()
    with app.test_client() as c:
        r = c.post("/api/char/recall", json={"char": "Aria"})
    assert r.status_code == 400


def test_char_recall_success_returns_200():
    with patch("app.calliope_shell.server.char_memory_recall",
               return_value={"snippets": [{"text": "snippet", "score": 0.9}]}):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/char/recall", json={"char": "Aria", "query": "battaglia"})
    assert r.status_code == 200


# --- /api/char/<name>/facts --------------------------------------------------


def test_char_facts_returns_200():
    with patch("app.calliope_shell.server.char_memory_list_facts",
               return_value={"facts": [{"text": "fatto", "scope": "L1"}]}):
        app = _make_app()
        with app.test_client() as c:
            r = c.get("/api/char/Aria/facts")
    assert r.status_code == 200
    assert "facts" in r.get_json()


def test_char_facts_scope_param_forwarded():
    captured = {}

    def fake_list(name, scope=None):
        captured["scope"] = scope
        return {"facts": []}

    with patch("app.calliope_shell.server.char_memory_list_facts", side_effect=fake_list):
        app = _make_app()
        with app.test_client() as c:
            c.get("/api/char/Aria/facts?scope=L2")
    assert captured["scope"] == "L2"
