"""Contract test (messages-import bridge) — selezione intelligente Yokai Discord-tuppers.

NESSUN import reale: contratto su FIXTURE. Il run reale su messages_clean.jsonl (32598)
resta GATED su decisione operatore (privacy + scope). Vedi .planning/CALLIOPE_MESSAGES_IMPORT_PLAN.md.

Regole (operator-mandate via father):
 (a) SOLO messaggi tupper: type=='IC' con character non-null.
 (b) SKIP system + OOC.
 (c) IC fuori da ogni scena (ts-range) → char_sheets, NON messaggi-scena.
 (d) char non-matchato nel DB → character_id NULL + author_name.
"""
import json

from app.db import get_db, init_schema
from app.db.characters import add_character
from app.messages_import import import_messages_to_db


def _write_jsonl(path, records):
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8")


def _seed(tmp_path):
    db = str(tmp_path / "t.db")
    conn = get_db(db)
    init_schema(conn)
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", ("scene_001", "La Taverna"))
    conn.commit()
    add_character(conn, name="Kikyo", kind="player")  # char matchabile
    conn.close()

    scenes = tmp_path / "scenes_raw.json"
    scenes.write_text(json.dumps([
        {"scene_id": "scene_001", "timestamp_start": "2021-11-19T01:00:00Z",
         "timestamp_end": "2021-11-19T02:00:00Z", "message_count": 2}
    ]), encoding="utf-8")

    msgs = tmp_path / "messages_clean.jsonl"
    _write_jsonl(msgs, [
        # IC dentro la scena, char matchato → messaggio-scena con character_id
        {"row_idx": 0, "timestamp": "2021-11-19T01:10:00Z", "player": "P1",
         "character": "Kikyo", "type": "IC", "message": "Entro nella taverna.", "original_message": None},
        # IC dentro la scena, char NON nel DB → messaggio con author_name + character_id NULL (regola d)
        {"row_idx": 1, "timestamp": "2021-11-19T01:20:00Z", "player": "P2",
         "character": "NPC: Oste", "type": "IC", "message": "Benvenuto.", "original_message": None},
        # OOC → skip (regola b)
        {"row_idx": 2, "timestamp": "2021-11-19T01:25:00Z", "player": "P1",
         "character": None, "type": "OOC", "message": "lol bella", "original_message": None},
        # system → skip (regola b)
        {"row_idx": 3, "timestamp": "2021-11-19T01:00:00Z", "player": "Horo",
         "character": None, "type": "system", "message": None, "original_message": None},
        # IC FUORI da ogni scena (ts oltre il range) → char_sheets, NON messaggio-scena (regola c)
        {"row_idx": 4, "timestamp": "2021-11-25T10:00:00Z", "player": "P1",
         "character": "Kikyo", "type": "IC", "message": "Scheda: Kikyo, kitsune...", "original_message": None},
    ])
    return db, str(scenes), str(msgs)


def test_only_ic_in_scene_become_messages(tmp_path):
    db, scenes, msgs = _seed(tmp_path)
    res = import_messages_to_db(msgs, scenes, db_path=db)
    assert res["messages"] == 2, "solo i 2 IC dentro la scena"
    conn = get_db(db)
    n = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    conn.close()
    assert n == 2


def test_system_and_ooc_skipped(tmp_path):
    db, scenes, msgs = _seed(tmp_path)
    res = import_messages_to_db(msgs, scenes, db_path=db)
    assert res["skipped_system_ooc"] == 2


def test_out_of_scene_ic_goes_to_char_sheets(tmp_path):
    db, scenes, msgs = _seed(tmp_path)
    res = import_messages_to_db(msgs, scenes, db_path=db)
    # l'IC fuori-scena (row_idx 4) NON è un messaggio-scena → char_sheets
    assert res["char_sheets"] == 1


def test_unmatched_char_null_id_keeps_author_name(tmp_path):
    db, scenes, msgs = _seed(tmp_path)
    import_messages_to_db(msgs, scenes, db_path=db)
    conn = get_db(db)
    row = conn.execute(
        "SELECT character_id, author_name FROM messages WHERE author_name = ?", ("NPC: Oste",)
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[0] is None, "char non-matchato → character_id NULL"
    assert row[1] == "NPC: Oste", "ma author_name preservato"


def test_idempotent(tmp_path):
    db, scenes, msgs = _seed(tmp_path)
    import_messages_to_db(msgs, scenes, db_path=db)
    import_messages_to_db(msgs, scenes, db_path=db)  # re-run
    conn = get_db(db)
    n = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    conn.close()
    assert n == 2, "re-run non duplica"
