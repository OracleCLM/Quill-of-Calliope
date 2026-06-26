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


def test_summary_messages_in_summary_section(tmp_path):
    p = tmp_path / "t.db"
    conn = get_db(p)
    init_schema(conn)
    sid = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (sid, "Scena Test"))
    conn.commit()
    add_message(conn, scene_id=sid, author_name="Sistema", content_original="Riassunto: epica battaglia.", is_summary=1, position_order=0)
    add_message(conn, scene_id=sid, author_name="Eroe", content_original="Avanziamo.", position_order=1)
    conn.close()
    ctx = build_scene_context(sid, db_path=str(p))
    assert "[Summary]" in ctx
    assert "Riassunto: epica battaglia." in ctx
    assert "[Recent messages]" in ctx
    assert "Eroe: Avanziamo." in ctx


def test_max_recent_caps_regular_messages(tmp_path):
    p = tmp_path / "t.db"
    conn = get_db(p)
    init_schema(conn)
    sid = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (sid, "Scena Cap"))
    conn.commit()
    for i in range(5):
        add_message(conn, scene_id=sid, author_name=f"A{i}", content_original=f"msg{i}", position_order=i)
    conn.close()
    ctx = build_scene_context(sid, db_path=str(p), max_recent=3)
    assert "msg0" not in ctx
    assert "msg1" not in ctx
    assert "msg2" in ctx and "msg3" in ctx and "msg4" in ctx
