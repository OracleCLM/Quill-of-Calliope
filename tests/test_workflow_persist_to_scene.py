"""Contract WI-PERSIST (workflow-integration, meta PERSISTENZA-OUT della VISION):
flag `persist` OPT-IN (default OFF) su /api/draft E /api/messages/next.

VISION = intent -> draft IN-CONTESTO -> PERSISTENZA. F1 ha chiuso il context-IN; questo chiude
il persist-OUT: quando persist=true il testo generato viene APPESO atomicamente alla scena-DB
(add_message) coi campi corretti (scene_id, author_name = personaggio-DB, content, ts);
quando persist e assente/false (default) NON scrive nulla (backward-compat: draft resta preview).

Doppio contract per ENTRAMBI gli endpoint (coerenza, mandato father):
  (1) persist=true  -> il msg compare in list_messages_for_scene coi campi giusti
  (2) persist=false -> nessuna scrittura (count invariato), risposta invariata (backward-compat)
"""
import json as _json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import get_db, init_schema  # noqa: E402
from app.db.characters import add_character, add_character_to_scene  # noqa: E402
from app.db.messages import list_messages_for_scene  # noqa: E402

GEN = "Zephyrina entra nella taverna TESTPERSIST"


def _seed(p: Path) -> None:
    conn = get_db(p)
    init_schema(conn)
    conn.execute(
        "INSERT INTO scenes(id, title, created_at, updated_at) "
        "VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%SZ','now'), strftime('%Y-%m-%dT%H:%M:%SZ','now'))",
        ("sc_p", "Taverna del Drago"),
    )
    cid = add_character(conn, name="Zephyrina", kind="npc",
                        card_json=_json.dumps({"traits": ["astuta"]}))
    add_character_to_scene(conn, "sc_p", cid)
    conn.commit()
    conn.close()


def _app(p: Path, monkeypatch):
    monkeypatch.setenv("CALLIOPE_DB_PATH", str(p))
    from app.calliope_shell.server import create_app
    app, _ = create_app()
    app.config["TESTING"] = True
    return app


def _mock_post():
    m = MagicMock()
    m.status_code = 200
    m.raise_for_status = MagicMock()
    m.json.return_value = {"result": GEN, "text": GEN, "content": GEN, "next_msg": GEN}
    return m


def _msgs(p: Path):
    conn = get_db(p)
    out = list_messages_for_scene(conn, "sc_p")
    conn.close()
    return out


def _appended_ok(msgs, author: str) -> bool:
    return any(
        m.get("author_name") == author
        and "TESTPERSIST" in (m.get("content_original") or "")
        and m.get("scene_id") == "sc_p"
        for m in msgs
    )


# ── /api/draft ────────────────────────────────────────────────────────────────
def test_draft_persist_true_appends_to_scene(tmp_path, monkeypatch):
    db = tmp_path / "c.db"
    _seed(db)
    app = _app(db, monkeypatch)
    with patch("requests.post", return_value=_mock_post()):
        with app.test_client() as c:
            r = c.post("/api/draft", json={
                "scene_id": "sc_p", "intent_it": "x",
                "char_focus": "Zephyrina", "persist": True,
            })
    assert r.status_code == 200
    assert _appended_ok(_msgs(db), "Zephyrina"), "draft persist=true non ha appeso il msg coi campi giusti"


def test_draft_persist_false_default_no_write(tmp_path, monkeypatch):
    db = tmp_path / "c.db"
    _seed(db)
    app = _app(db, monkeypatch)
    with patch("requests.post", return_value=_mock_post()):
        with app.test_client() as c:
            r = c.post("/api/draft", json={
                "scene_id": "sc_p", "intent_it": "x", "char_focus": "Zephyrina",
            })
    assert r.status_code == 200 and r.get_json().get("draft_text")
    assert _msgs(db) == [], "persist=false default NON deve scrivere (backward-compat)"


# ── /api/messages/next ────────────────────────────────────────────────────────
def test_next_persist_true_appends_to_scene(tmp_path, monkeypatch):
    db = tmp_path / "c.db"
    _seed(db)
    app = _app(db, monkeypatch)
    with patch("requests.post", return_value=_mock_post()):
        with app.test_client() as c:
            r = c.post("/api/messages/next", json={
                "scene_id": "sc_p", "char": "Zephyrina", "persist": True,
            })
    assert r.status_code == 200
    assert _appended_ok(_msgs(db), "Zephyrina"), "messages/next persist=true non ha appeso il msg coi campi giusti"


def test_next_persist_false_default_no_write(tmp_path, monkeypatch):
    db = tmp_path / "c.db"
    _seed(db)
    app = _app(db, monkeypatch)
    with patch("requests.post", return_value=_mock_post()):
        with app.test_client() as c:
            r = c.post("/api/messages/next", json={
                "scene_id": "sc_p", "char": "Zephyrina",
            })
    assert r.status_code == 200
    assert _msgs(db) == [], "persist=false default NON deve scrivere (backward-compat)"
