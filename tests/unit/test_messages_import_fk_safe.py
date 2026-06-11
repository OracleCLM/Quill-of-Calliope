"""Contract test MSGIMP-3 (FK-safe) — scoperto dal full-run reale.

Il full-run su prod ha dato FOREIGN KEY constraint failed: scenes_raw.json ha 332 scene ma
il DB ne ha 303 (29 malformate non migrate, gap F2). I messaggi che cadono nelle ts-range
delle 29 scene mancanti referenziano uno scene_id NON nel DB → FK fail.

Fix: il bridge deve essere FK-safe — skippare i messaggi la cui scena risolta NON è nel DB
(contarli in skipped_no_scene), senza sollevare. Le scene presenti funzionano normalmente.
"""
import json

from app.db import get_db, init_schema
from app.db.characters import add_character
from app.messages_import import import_messages_to_db


def _seed(tmp_path):
    db = str(tmp_path / "t.db")
    conn = get_db(db)
    init_schema(conn)
    # solo scene_001 nel DB; scene_999 NO (simula scena malformata non migrata)
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", ("scene_001", "Presente"))
    conn.commit()
    add_character(conn, name="Kikyo", kind="player")
    conn.close()

    scenes = tmp_path / "scenes_raw.json"
    scenes.write_text(json.dumps([
        {"scene_id": "scene_001", "timestamp_start": "2021-11-19T01:00:00Z",
         "timestamp_end": "2021-11-19T02:00:00Z"},
        {"scene_id": "scene_999", "timestamp_start": "2021-11-20T01:00:00Z",
         "timestamp_end": "2021-11-20T02:00:00Z"},  # NON nel DB
    ]), encoding="utf-8")

    msgs = tmp_path / "messages_clean.jsonl"
    msgs.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in [
        {"row_idx": 0, "timestamp": "2021-11-19T01:10:00Z", "player": "P1",
         "character": "Kikyo", "type": "IC", "message": "In scena presente.", "original_message": None},
        {"row_idx": 1, "timestamp": "2021-11-20T01:10:00Z", "player": "P1",
         "character": "Kikyo", "type": "IC", "message": "In scena MANCANTE.", "original_message": None},
    ]), encoding="utf-8")
    return db, str(scenes), str(msgs)


def test_no_fk_error_on_missing_scene(tmp_path):
    db, scenes, msgs = _seed(tmp_path)
    # NON deve sollevare IntegrityError
    res = import_messages_to_db(msgs, scenes, db_path=db)
    assert res["messages"] == 1, "solo il msg della scena PRESENTE entra"


def test_missing_scene_counted_skipped_no_scene(tmp_path):
    db, scenes, msgs = _seed(tmp_path)
    res = import_messages_to_db(msgs, scenes, db_path=db)
    assert "skipped_no_scene" in res
    assert res["skipped_no_scene"] == 1, "il msg della scena non-in-DB è skipped_no_scene"


def test_present_scene_message_persisted(tmp_path):
    db, scenes, msgs = _seed(tmp_path)
    import_messages_to_db(msgs, scenes, db_path=db)
    conn = get_db(db)
    n = conn.execute("SELECT COUNT(*) FROM messages WHERE scene_id = ?", ("scene_001",)).fetchone()[0]
    conn.close()
    assert n == 1
