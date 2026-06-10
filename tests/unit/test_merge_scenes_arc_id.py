"""
Contract test (father-authored acceptance) — WI-53.

Il worker Efesto deve far passare questi test correggendo in
`app/db/messages.py` la funzione merge_scenes (riga ~577):

    BUG: INSERT INTO scenes(id, title, created_at, updated_at)
         NON copia arc_id dalla scena sorgente (stessa issue di WI-51 su duplicate_scene).

    FIX: usare arc_id della scena A (la "primaria") nella scena unita:
        cur.execute("SELECT arc_id FROM scenes WHERE id = ?", (scene_id_a,))
        arc_row = cur.fetchone()
        merged_arc_id = arc_row[0] if arc_row else None

        cur.execute(
            "INSERT INTO scenes(id, title, arc_id, created_at, updated_at)"
            " VALUES(?, ?, ?, datetime('now'), datetime('now'))",
            (new_scene_id, new_name, merged_arc_id),
        )

Comportamento atteso:
  - Scena A ha arc_id X -> merged.arc_id == X
  - Scena A senza arc_id -> merged.arc_id == NULL
  - I messaggi di entrambe le scene sono presenti nella merged (non-regressione)

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest

from app.db import get_db, init_schema, new_id
from app.db.messages import add_message, list_messages_for_scene, merge_scenes


@pytest.fixture
def conn(tmp_path):
    p = tmp_path / "test.db"
    c = get_db(p)
    init_schema(c)
    yield c
    c.close()


@pytest.fixture
def scenes_with_arc(conn):
    arc_id = new_id()
    sid_a = new_id()
    sid_b = new_id()
    conn.execute("INSERT INTO arcs (id, title) VALUES (?, ?)", (arc_id, "Arco Alpha"))
    conn.execute(
        "INSERT INTO scenes (id, title, arc_id) VALUES (?, ?, ?)", (sid_a, "Scena A", arc_id)
    )
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (sid_b, "Scena B"))
    add_message(conn, scene_id=sid_a, author_name="A", content_original="msgA", position_order=0)
    add_message(conn, scene_id=sid_b, author_name="B", content_original="msgB", position_order=0)
    conn.commit()
    return {"sid_a": sid_a, "sid_b": sid_b, "arc_id": arc_id}


@pytest.fixture
def scenes_no_arc(conn):
    sid_a = new_id()
    sid_b = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (sid_a, "Scena A"))
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (sid_b, "Scena B"))
    add_message(conn, scene_id=sid_a, author_name="A", content_original="msgA", position_order=0)
    add_message(conn, scene_id=sid_b, author_name="B", content_original="msgB", position_order=0)
    conn.commit()
    return {"sid_a": sid_a, "sid_b": sid_b}


# --- WI-53: merge_scenes copia arc_id da scena A ----------------------------

def test_merge_preserves_arc_id_from_a(conn, scenes_with_arc):
    s = scenes_with_arc
    merged_id = merge_scenes(conn, s["sid_a"], s["sid_b"], "Merged")
    row = conn.execute("SELECT arc_id FROM scenes WHERE id = ?", (merged_id,)).fetchone()
    assert row is not None
    assert row[0] == s["arc_id"]


def test_merge_null_arc_stays_null(conn, scenes_no_arc):
    s = scenes_no_arc
    merged_id = merge_scenes(conn, s["sid_a"], s["sid_b"], "Merged No Arc")
    row = conn.execute("SELECT arc_id FROM scenes WHERE id = ?", (merged_id,)).fetchone()
    assert row is not None
    assert row[0] is None


def test_merge_combines_messages(conn, scenes_with_arc):
    s = scenes_with_arc
    merged_id = merge_scenes(conn, s["sid_a"], s["sid_b"], "Merged")
    msgs = list(list_messages_for_scene(conn, merged_id))
    assert len(msgs) == 2
    contents = {m["content_original"] for m in msgs}
    assert contents == {"msgA", "msgB"}
