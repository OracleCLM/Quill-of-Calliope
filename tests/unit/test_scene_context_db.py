"""Contract test VG-1 (gap-review F1): scene-context per il draft-gen deve leggere il DB.

FATALE F1: /api/messages/next (draft-gen) legge i flat-YAML, non il DB scene-as-chat.
Questo helper DB-aware è il primo mattone di chiusura: il draft-gen lo userà per
comporre il contesto-scena dal DB (titolo + ultimi messaggi ordinati).
"""
from app.db import get_db, init_schema, new_id
from app.db.messages import add_message
from app.scene_context import build_scene_context


def _seed(tmp_path):
    p = tmp_path / "t.db"
    conn = get_db(p)
    init_schema(conn)
    sid = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (sid, "La Taverna del Drago"))
    conn.commit()
    add_message(conn, scene_id=sid, author_name="Aelar", content_original="Benvenuto.", position_order=0)
    add_message(conn, scene_id=sid, author_name="Mara", content_original="Grazie, oste.", position_order=1)
    conn.close()
    return str(p), sid


def test_context_includes_scene_title(tmp_path):
    db, sid = _seed(tmp_path)
    ctx = build_scene_context(sid, db_path=db)
    assert "La Taverna del Drago" in ctx


def test_context_includes_recent_messages(tmp_path):
    db, sid = _seed(tmp_path)
    ctx = build_scene_context(sid, db_path=db)
    assert "Aelar" in ctx and "Benvenuto." in ctx
    assert "Mara" in ctx and "Grazie, oste." in ctx


def test_unknown_scene_returns_empty(tmp_path):
    db, _ = _seed(tmp_path)
    assert build_scene_context("inesistente", db_path=db) == ""
