"""
Contract test (father-authored acceptance) — WI-51.

Il worker Efesto deve far passare questi test correggendo in
`app/db/messages.py` la funzione duplicate_scene (riga ~531):

    BUG: INSERT INTO scenes(id, title, created_at, updated_at)
         NON copia arc_id dalla scena sorgente.

    FIX: leggere arc_id dalla scena sorgente e includerlo nell'INSERT:
        cur.execute("SELECT arc_id FROM scenes WHERE id = ?", (scene_id,))
        arc_row = cur.fetchone()
        source_arc_id = arc_row[0] if arc_row else None

        cur.execute(
            "INSERT INTO scenes(id, title, arc_id, created_at, updated_at)"
            " VALUES(?, ?, ?, datetime('now'), datetime('now'))",
            (new_scene_id, new_name, source_arc_id),
        )

Comportamento atteso post-fix:
  - Scena con arc_id -> duplicata -> duplicata.arc_id == originale.arc_id
  - Scena senza arc_id -> duplicata -> duplicata.arc_id e' NULL
  - I messaggi duplicati devono restare invariati (test di non-regressione)

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest

from app.db import get_db, init_schema, new_id
from app.db.messages import add_message, duplicate_scene, list_messages_for_scene


@pytest.fixture
def conn(tmp_path):
    p = tmp_path / "test.db"
    c = get_db(p)
    init_schema(c)
    yield c
    c.close()


@pytest.fixture
def scene_with_arc(conn):
    arc_id = new_id()
    scene_id = new_id()
    conn.execute("INSERT INTO arcs (id, title) VALUES (?, ?)", (arc_id, "Arco Test"))
    conn.execute(
        "INSERT INTO scenes (id, title, arc_id) VALUES (?, ?, ?)",
        (scene_id, "Scena Originale", arc_id),
    )
    add_message(conn, scene_id=scene_id, author_name="A", content_original="msg1", position_order=0)
    add_message(conn, scene_id=scene_id, author_name="B", content_original="msg2", position_order=1)
    conn.commit()
    return {"scene_id": scene_id, "arc_id": arc_id}


@pytest.fixture
def scene_no_arc(conn):
    scene_id = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "Scena Senza Arco"))
    add_message(conn, scene_id=scene_id, author_name="C", content_original="msg3", position_order=0)
    conn.commit()
    return {"scene_id": scene_id}


# --- WI-51: duplicate_scene copia arc_id ------------------------------------

def test_duplicate_preserves_arc_id(conn, scene_with_arc):
    new_id_ = duplicate_scene(conn, scene_with_arc["scene_id"], "Copia Scena")
    row = conn.execute("SELECT arc_id FROM scenes WHERE id = ?", (new_id_,)).fetchone()
    assert row is not None
    assert row[0] == scene_with_arc["arc_id"]


def test_duplicate_null_arc_stays_null(conn, scene_no_arc):
    new_id_ = duplicate_scene(conn, scene_no_arc["scene_id"], "Copia Senza Arco")
    row = conn.execute("SELECT arc_id FROM scenes WHERE id = ?", (new_id_,)).fetchone()
    assert row is not None
    assert row[0] is None


def test_duplicate_copies_messages(conn, scene_with_arc):
    new_id_ = duplicate_scene(conn, scene_with_arc["scene_id"], "Copia")
    msgs = list(list_messages_for_scene(conn, new_id_))
    assert len(msgs) == 2
    contents = {m["content_original"] for m in msgs}
    assert contents == {"msg1", "msg2"}
