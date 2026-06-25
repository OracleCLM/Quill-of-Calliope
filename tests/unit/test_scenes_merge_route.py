"""
Contract test (father-authored acceptance) — WI-21.

Il worker Efesto deve far passare questi test aggiungendo in
`app/calliope_shell/scenes_db_routes.py`:

    POST /api/db/scenes/merge
    body JSON: {"scene_id_a": str, "scene_id_b": str, "new_name": str}
    -> 201 + {"merged_scene_id": "<uuid>"}
    -> 400 se manca scene_id_a, scene_id_b, o new_name
    -> 404 se una delle due scene non esiste

NOTA: merge_scenes crea una NUOVA scena con messaggi A poi B.
Le scene originali rimangono nel DB (non vengono eliminate).

Usa SOLO: db_messages.merge_scenes(conn, scene_id_a, scene_id_b, new_name) -> str
  app/db/messages.py:577 — ritorna id della nuova scena.

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema, new_id
from app.db.messages import add_message
from app.calliope_shell.scenes_db_routes import register_scenes_db_routes


@pytest.fixture
def seeded(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    sid_a = new_id()
    sid_b = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (sid_a, "Scena A"))
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (sid_b, "Scena B"))
    conn.commit()
    add_message(conn, scene_id=sid_a, author_name="Alice",
                content_original="msg-A1", position_order=0)
    add_message(conn, scene_id=sid_a, author_name="Alice",
                content_original="msg-A2", position_order=1)
    add_message(conn, scene_id=sid_b, author_name="Bob",
                content_original="msg-B1", position_order=0)
    conn.close()
    return {"path": str(p), "sid_a": sid_a, "sid_b": sid_b}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# --- WI-21: merge scenes ----------------------------------------------------

def test_merge_returns_201_with_new_id(client):
    c, s = client
    r = c.post("/api/db/scenes/merge",
               json={"scene_id_a": s["sid_a"], "scene_id_b": s["sid_b"],
                     "new_name": "Merged"})
    assert r.status_code == 201
    body = r.get_json()
    assert "merged_scene_id" in body
    assert body["merged_scene_id"] not in (s["sid_a"], s["sid_b"])


def test_merge_new_scene_has_all_messages(client):
    c, s = client
    merged_id = c.post("/api/db/scenes/merge",
                       json={"scene_id_a": s["sid_a"], "scene_id_b": s["sid_b"],
                             "new_name": "Merged"}).get_json()["merged_scene_id"]
    detail = c.get(f"/api/db/scenes/{merged_id}").get_json()
    assert len(detail["messages"]) == 3
    contents = {m["content_original"] for m in detail["messages"]}
    assert contents == {"msg-A1", "msg-A2", "msg-B1"}


def test_merge_originals_still_exist(client):
    c, s = client
    c.post("/api/db/scenes/merge",
           json={"scene_id_a": s["sid_a"], "scene_id_b": s["sid_b"],
                 "new_name": "Merged"})
    assert c.get(f"/api/db/scenes/{s['sid_a']}").status_code == 200
    assert c.get(f"/api/db/scenes/{s['sid_b']}").status_code == 200


def test_merge_missing_fields_400(client):
    c, s = client
    r = c.post("/api/db/scenes/merge",
               json={"scene_id_a": s["sid_a"], "new_name": "Merged"})  # manca scene_id_b
    assert r.status_code == 400


def test_merge_unknown_scene_404(client):
    c, s = client
    r = c.post("/api/db/scenes/merge",
               json={"scene_id_a": s["sid_a"], "scene_id_b": "scena-inesistente",
                     "new_name": "Merged"})
    assert r.status_code == 404


def test_merge_value_error_from_db_function_404(client):
    """Lines 195-197: merge_scenes lancia ValueError → 404 not_found."""
    from unittest.mock import patch
    import app.db.messages as db_messages

    c, s = client
    with patch.object(db_messages, "merge_scenes", side_effect=ValueError("conflict")):
        r = c.post("/api/db/scenes/merge",
                   json={"scene_id_a": s["sid_a"], "scene_id_b": s["sid_b"],
                         "new_name": "Merged"})
    assert r.status_code == 404
    assert r.get_json()["error"] == "not_found"
