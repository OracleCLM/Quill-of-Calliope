"""
Contract test (father-authored acceptance) — WI-3/WI-4/WI-5/WI-9.

Cabla gli endpoint DB-backed scene-as-chat dentro Flask. Il worker Efesto deve
far passare questi test riempiendo i corpi route in
`app/calliope_shell/scenes_db_routes.py` (marcati TODO). NON modificare le
assertion: sono il contratto di accettazione.

Schema gia' esistente (NON crearne di nuovo): tabelle scenes / messages /
scene_reactions da migration 001+002. FK enforced (PRAGMA foreign_keys=ON):
scene_reactions.character_id -> characters.id, .message_id -> messages.id.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema, new_id
from app.db.messages import add_message
from app.calliope_shell.scenes_db_routes import register_scenes_db_routes


@pytest.fixture
def seeded(tmp_path):
    """DB temp con 1 scena + 2 messaggi + 1 personaggio (per le reazioni)."""
    p = tmp_path / "calliope_test.db"
    conn = get_db(p)
    init_schema(conn)
    scene_id = new_id()
    char_id = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (scene_id, "Test Scene"))
    conn.execute("INSERT INTO characters (id, name) VALUES (?, ?)", (char_id, "Alice"))
    conn.commit()
    add_message(conn, scene_id=scene_id, author_name="Alice",
                content_original="hello", position_order=0)
    add_message(conn, scene_id=scene_id, author_name="Bob",
                content_original="world", position_order=1)
    conn.close()
    return {"path": str(p), "scene_id": scene_id, "char_id": char_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config.update(TESTING=True)
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# --- WI-9: wiring smoke ---------------------------------------------------
def test_db_scenes_route_registered(client):
    c, _ = client
    rules = {r.rule for r in c.application.url_map.iter_rules()}
    assert "/api/db/scenes" in rules


# --- WI-3: list / detail --------------------------------------------------
def test_list_scenes(client):
    c, s = client
    r = c.get("/api/db/scenes")
    assert r.status_code == 200
    ids = [sc["id"] for sc in r.get_json()["scenes"]]
    assert s["scene_id"] in ids


def test_scene_detail_with_messages(client):
    c, s = client
    r = c.get(f"/api/db/scenes/{s['scene_id']}")
    assert r.status_code == 200
    data = r.get_json()
    assert data["scene"]["id"] == s["scene_id"]
    assert len(data["messages"]) == 2


def test_scene_detail_missing_404(client):
    c, _ = client
    r = c.get("/api/db/scenes/does-not-exist")
    assert r.status_code == 404


# --- WI-4: append message -------------------------------------------------
def test_append_message(client):
    c, s = client
    r = c.post(f"/api/db/scenes/{s['scene_id']}/messages",
               json={"author_name": "Carol", "content_original": "new msg"})
    assert r.status_code == 201
    detail = c.get(f"/api/db/scenes/{s['scene_id']}").get_json()
    assert len(detail["messages"]) == 3


def test_append_message_missing_scene_404(client):
    c, _ = client
    r = c.post("/api/db/scenes/nope/messages",
               json={"author_name": "X", "content_original": "y"})
    assert r.status_code == 404


# --- WI-5: reactions roundtrip --------------------------------------------
def test_reactions_add_and_list(client):
    c, s = client
    mid = c.get(f"/api/db/scenes/{s['scene_id']}").get_json()["messages"][0]["id"]
    r = c.post(f"/api/db/messages/{mid}/reactions",
               json={"character_id": s["char_id"], "emoji": "fire"})
    assert r.status_code == 201
    lst = c.get(f"/api/db/messages/{mid}/reactions").get_json()
    assert len(lst["reactions"]) == 1
    assert lst["reactions"][0]["emoji"] == "fire"
