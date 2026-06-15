"""Contract test (follow-up char_sheets PERSISTENCE) — regola (c) completa.

Il bridge MSGIMP-1 CONTA i char_sheets (IC fuori-scena) ma non li PERSISTE. Father ha
approvato il follow-up: gli IC fuori da ogni scena (il canale schede-personaggio) vanno
SCRITTI in una tabella `character_sheets` (utile per i char card), separati dai messaggi-scena.

Richiede: migration 005_character_sheets.sql (tabella) + il bridge che inserisce lì.
NESSUN import reale: contratto su fixture. Run reale resta gated operatore.
"""
import json

from app.db import get_db, init_schema
from app.db.characters import add_character
from app.messages_import import import_messages_to_db


def _seed(tmp_path):
    db = str(tmp_path / "t.db")
    conn = get_db(db)
    init_schema(conn)
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", ("scene_001", "La Taverna"))
    conn.commit()
    add_character(conn, name="Kikyo", kind="player")
    conn.close()

    scenes = tmp_path / "scenes_raw.json"
    scenes.write_text(json.dumps([
        {"scene_id": "scene_001", "timestamp_start": "2021-11-19T01:00:00Z",
         "timestamp_end": "2021-11-19T02:00:00Z", "message_count": 1}
    ]), encoding="utf-8")

    msgs = tmp_path / "messages_clean.jsonl"
    msgs.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in [
        # IC dentro la scena -> messaggio-scena
        {"row_idx": 0, "timestamp": "2021-11-19T01:10:00Z", "player": "P1",
         "character": "Kikyo", "type": "IC", "message": "Entro.", "original_message": None},
        # IC FUORI scena (canale schede) -> character_sheets
        {"row_idx": 1, "timestamp": "2021-11-25T10:00:00Z", "player": "P1",
         "character": "Kikyo", "type": "IC", "message": "Scheda: Kikyo, kitsune delle nevi.",
         "original_message": None},
    ]), encoding="utf-8")
    return db, str(scenes), str(msgs)


def test_char_sheets_persisted_to_table(tmp_path):
    db, scenes, msgs = _seed(tmp_path)
    res = import_messages_to_db(msgs, scenes, db_path=db)
    assert res["char_sheets"] == 1
    conn = get_db(db)
    rows = conn.execute(
        "SELECT character_name, content FROM character_sheets WHERE character_name = ?", ("Kikyo",)
    ).fetchall()
    conn.close()
    assert len(rows) == 1, "l'IC fuori-scena deve essere persistito in character_sheets"
    assert "Scheda" in rows[0]["content"]


def test_char_sheets_resolves_character_id_when_known(tmp_path):
    db, scenes, msgs = _seed(tmp_path)
    import_messages_to_db(msgs, scenes, db_path=db)
    conn = get_db(db)
    row = conn.execute(
        "SELECT character_id FROM character_sheets WHERE character_name = ?", ("Kikyo",)
    ).fetchone()
    conn.close()
    assert row is not None and row[0] is not None, "Kikyo è nel DB → character_id risolto"


def test_char_sheets_idempotent(tmp_path):
    db, scenes, msgs = _seed(tmp_path)
    import_messages_to_db(msgs, scenes, db_path=db)
    import_messages_to_db(msgs, scenes, db_path=db)
    conn = get_db(db)
    n = conn.execute("SELECT COUNT(*) FROM character_sheets").fetchone()[0]
    conn.close()
    assert n == 1, "re-run non duplica le schede"
