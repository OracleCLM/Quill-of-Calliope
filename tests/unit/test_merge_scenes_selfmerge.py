"""
Contract test (father-authored acceptance) — WI-52.

Il worker Efesto deve far passare questi test aggiungendo:

1. In `app/db/messages.py` — funzione merge_scenes (riga ~577):
       Guard iniziale contro self-merge:
         if scene_id_a == scene_id_b:
             raise ValueError("cannot merge a scene with itself")

2. Nella route POST /api/db/scenes/merge in `scenes_db_routes.py`:
       Catturare ValueError da merge_scenes e ritornare 400:
         except ValueError:
             return jsonify({"error": "bad_request"}), 400

   NOTA: la route attuale cattura solo ValueError per "not_found" -> 404.
   Serve distinguere: ValueError("not_found") -> 404 vs ValueError(self-merge) -> 400.
   Strategia suggerita: usare messaggi specifici o eccezioni distinte.
   Alternativa minima: aggiungere guard PRIMA di chiamare merge_scenes nella route:
     if body["scene_id_a"] == body["scene_id_b"]:
         return jsonify({"error": "bad_request"}), 400

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest

from app.db import get_db, init_schema, new_id
from app.db.messages import add_message, merge_scenes


# --- WI-52: merge_scenes self-merge DB guard --------------------------------

@pytest.fixture
def conn(tmp_path):
    p = tmp_path / "test.db"
    c = get_db(p)
    init_schema(c)
    yield c
    c.close()


@pytest.fixture
def scene_id(conn):
    sid = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (sid, "Scena"))
    add_message(conn, scene_id=sid, author_name="A", content_original="msg", position_order=0)
    conn.commit()
    return sid


def test_self_merge_raises_value_error(conn, scene_id):
    with pytest.raises(ValueError):
        merge_scenes(conn, scene_id, scene_id, "Self-Merged")


# --- WI-52: route 400 su self-merge -----------------------------------------

def test_self_merge_route_returns_400():
    from flask import Flask
    from app.calliope_shell.scenes_db_routes import register_scenes_db_routes
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "test.db"
        conn = get_db(p)
        init_schema(conn)
        sid = new_id()
        conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (sid, "S"))
        conn.commit()
        conn.close()

        app = Flask(__name__)
        app.config["TESTING"] = True
        register_scenes_db_routes(app, db_path=str(p))
        c = app.test_client()

        r = c.post(
            "/api/db/scenes/merge",
            json={"scene_id_a": sid, "scene_id_b": sid, "new_name": "Self"},
        )
        assert r.status_code == 400
