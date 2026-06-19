"""Contract WI-VG-CHARCTX (F1 residuo): /api/draft deve includere il CONTESTO-PERSONAGGI
da DB quando scene_id e' una scena-DB, non solo da flat-YAML.

F1 core (scene_ctx) gia' chiuso da VG-1b. Residuo: il char-context resta YAML-bound su 2 layer:
  (1) `participants` <- _SCENES_DIR.glob (server.py:1120, "compat-YAML")
  (2) `_load_char_sheets` <- _CHARS_DIR.glob (YAML-only)
=> per una scena DB-only, participants=[] -> char_sheets=[] -> draft SENZA contesto-personaggi.

Schema-verdict: il DB CONTIENE gia' i dati-sheet (characters.card_json + tabella character_sheets,
migration 005) -> NON e' decisione data-model. Fix = estendere il pattern VG-1b (DB-first + fallback YAML)
ai DUE layer: participants via list_characters_in_scene, char_sheets dal record DB (name + card_json).

Questo contract verifica il chain END-TO-END: seed scena+personaggio nel DB, scene_characters,
poi POST /api/draft -> il prompt inviato all'LLM deve contenere il NOME del personaggio-DB
(sheets_text rende `[{name}] ...`). RED finche' il char-context non e' DB-first.
"""
import json as _json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import get_db, init_schema  # noqa: E402
from app.db.characters import add_character, add_character_to_scene  # noqa: E402


def _seed_db(p: Path) -> None:
    conn = get_db(p)
    init_schema(conn)
    conn.execute(
        "INSERT INTO scenes(id, title, created_at, updated_at) "
        "VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%SZ','now'), strftime('%Y-%m-%dT%H:%M:%SZ','now'))",
        ("scene_vgctx", "Taverna del Drago"),
    )
    cid = add_character(
        conn,
        name="Zephyrina Testchar",
        kind="npc",
        card_json=_json.dumps({"traits": ["astuta"], "backstory": "mercante errante"}),
    )
    add_character_to_scene(conn, "scene_vgctx", cid)
    conn.commit()
    conn.close()


def test_draft_includes_db_character_context(tmp_path, monkeypatch):
    db = tmp_path / "calliope_test.db"
    _seed_db(db)
    monkeypatch.setenv("CALLIOPE_DB_PATH", str(db))

    from app.calliope_shell.server import create_app

    app, _ = create_app()
    app.config["TESTING"] = True

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": "Draft con contesto."}
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp) as mpost:
        with app.test_client() as c:
            r = c.post("/api/draft", json={
                "scene_id": "scene_vgctx",
                "intent_it": "Zephyrina entra nella taverna",
            })

    assert r.status_code == 200
    # il prompt inviato all'LLM deve includere il personaggio-DB della scena
    sent = _json.dumps([{"a": mpost.call_args.args, "k": str(mpost.call_args.kwargs)}], default=str)
    assert "Zephyrina Testchar" in sent, (
        "il draft NON include il contesto-personaggi dal DB (char-context ancora YAML-bound, F1 residuo aperto)"
    )
