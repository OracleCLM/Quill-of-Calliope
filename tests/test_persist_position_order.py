"""Contract WI-PERSIST-ORDER: il messaggio persistito (persist=true) deve essere APPESO
in coda alla scena (position_order corretto), NON collidere a 0 coi messaggi esistenti.

Gap (classe incoerenze-messages): add_message usa position_order=0 di default e non auto-incrementa;
il persist di WI-PERSIST appende con pos=0 -> in una scena che ha gia messaggi il nuovo msg
collide a position 0 e appare nel posto SBAGLIATO nella scene-as-chat (ordinata per position_order).
Completezza-semantica: il persist deve calcolare la posizione di coda.

Contract: scena con 1 msg esistente (pos 0) -> /api/draft persist=true -> il msg generato ha
position_order DISTINTO e MAGGIORE (in coda), nessuna collisione.
"""
import json as _json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import get_db, init_schema  # noqa: E402
from app.db.characters import add_character, add_character_to_scene  # noqa: E402
from app.db.messages import add_message, list_messages_for_scene  # noqa: E402

GEN = "Zephyrina entra TESTORDER"


def _seed(p: Path) -> None:
    conn = get_db(p)
    init_schema(conn)
    conn.execute(
        "INSERT INTO scenes(id, title, created_at, updated_at) "
        "VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%SZ','now'), strftime('%Y-%m-%dT%H:%M:%SZ','now'))",
        ("sc_o", "Taverna"),
    )
    cid = add_character(conn, name="Zephyrina", kind="npc",
                        card_json=_json.dumps({"traits": ["astuta"]}))
    add_character_to_scene(conn, "sc_o", cid)
    # messaggio gia esistente in coda (position 0)
    add_message(conn, scene_id="sc_o", author_name="Narratore",
                content_original="messaggio esistente", position_order=0)
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


def test_persisted_message_appended_at_end_no_collision(tmp_path, monkeypatch):
    db = tmp_path / "c.db"
    _seed(db)
    app = _app(db, monkeypatch)
    with patch("requests.post", return_value=_mock_post()):
        with app.test_client() as c:
            r = c.post("/api/draft", json={
                "scene_id": "sc_o", "intent_it": "x",
                "char_focus": "Zephyrina", "persist": True,
            })
    assert r.status_code == 200
    conn = get_db(db)
    msgs = list_messages_for_scene(conn, "sc_o")
    conn.close()
    assert len(msgs) == 2, "il msg persistito non e stato appeso"
    positions = sorted(m.get("position_order") for m in msgs)
    assert positions[0] != positions[1], "collisione position_order (entrambi 0) — ordine rotto"
    gen = next(m for m in msgs if "TESTORDER" in (m.get("content_original") or ""))
    assert gen["position_order"] >= 1, "il msg generato non e in coda (position_order non incrementato)"
