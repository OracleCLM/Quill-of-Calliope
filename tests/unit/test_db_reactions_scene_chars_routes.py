"""GAP-44: test unitari per reactions_db_routes + scene_characters_db_routes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from flask import Flask

from app.db import get_db, init_schema, new_id
from app.calliope_shell.reactions_db_routes import register_reactions_db_routes
from app.calliope_shell.scene_characters_db_routes import register_scene_characters_db_routes


# ── Shared fixture helpers ────────────────────────────────────────────────────


@pytest.fixture
def db_path(tmp_path):
    p = str(tmp_path / "test.db")
    conn = get_db(p)
    init_schema(conn)
    conn.close()
    return p


def _scene(db_path, title="Scena Test"):
    sid = new_id()
    conn = get_db(db_path)
    conn.execute(
        "INSERT INTO scenes(id, title, created_at, updated_at) "
        "VALUES(?,?,datetime('now'),datetime('now'))",
        (sid, title),
    )
    conn.commit()
    conn.close()
    return sid


def _char(db_path, name="Aurora"):
    cid = new_id()
    conn = get_db(db_path)
    conn.execute(
        "INSERT INTO characters(id, name, created_at, updated_at) "
        "VALUES(?,?,datetime('now'),datetime('now'))",
        (cid, name),
    )
    conn.commit()
    conn.close()
    return cid


def _msg(db_path, scene_id):
    mid = new_id()
    conn = get_db(db_path)
    conn.execute(
        "INSERT INTO messages(id, scene_id, author_name, content_original, "
        "position_order, ts) VALUES(?,?,?,?,0,datetime('now'))",
        (mid, scene_id, "Aurora", "testo"),
    )
    conn.commit()
    conn.close()
    return mid


# ── reactions_db_routes ───────────────────────────────────────────────────────


@pytest.fixture
def reactions_client(db_path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_reactions_db_routes(app, db_path=db_path)
    return app.test_client(), db_path


def test_list_reactions_empty(reactions_client):
    client, _ = reactions_client
    mid = new_id()
    r = client.get(f"/api/db/messages/{mid}/reactions")
    assert r.status_code == 200
    assert r.get_json()["reactions"] == []


def test_list_reactions_returns_added(reactions_client):
    client, db = reactions_client
    sid = _scene(db)
    mid = _msg(db, sid)
    cid = _char(db)
    client.post(
        f"/api/db/messages/{mid}/reactions",
        json={"character_id": cid, "emoji": "❤️"},
    )
    r = client.get(f"/api/db/messages/{mid}/reactions")
    assert r.status_code == 200
    data = r.get_json()["reactions"]
    assert len(data) == 1
    assert data[0]["emoji"] == "❤️"


def test_add_reaction_missing_character_id(reactions_client):
    client, db = reactions_client
    sid = _scene(db)
    mid = _msg(db, sid)
    r = client.post(f"/api/db/messages/{mid}/reactions", json={"emoji": "👍"})
    assert r.status_code == 400


def test_add_reaction_message_not_found(reactions_client):
    client, db = reactions_client
    cid = _char(db)
    r = client.post(
        f"/api/db/messages/{new_id()}/reactions",
        json={"character_id": cid, "emoji": "👍"},
    )
    assert r.status_code == 404


def test_add_reaction_returns_201(reactions_client):
    client, db = reactions_client
    sid = _scene(db)
    mid = _msg(db, sid)
    cid = _char(db)
    r = client.post(
        f"/api/db/messages/{mid}/reactions",
        json={"character_id": cid, "emoji": "⭐"},
    )
    assert r.status_code == 201
    assert "id" in r.get_json()


def test_delete_reaction_204(reactions_client):
    client, db = reactions_client
    sid = _scene(db)
    mid = _msg(db, sid)
    cid = _char(db)
    resp = client.post(
        f"/api/db/messages/{mid}/reactions",
        json={"character_id": cid, "emoji": "👍"},
    )
    rid = resp.get_json()["id"]
    r = client.delete(f"/api/db/messages/{mid}/reactions/{rid}")
    assert r.status_code == 204


def test_delete_reaction_not_found_404(reactions_client):
    client, db = reactions_client
    sid = _scene(db)
    mid = _msg(db, sid)
    r = client.delete(f"/api/db/messages/{mid}/reactions/{new_id()}")
    assert r.status_code == 404


# ── scene_characters_db_routes ────────────────────────────────────────────────


@pytest.fixture
def sc_client(db_path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scene_characters_db_routes(app, db_path=db_path)
    return app.test_client(), db_path


def test_list_scene_chars_scene_not_found(sc_client):
    client, _ = sc_client
    r = client.get(f"/api/db/scenes/{new_id()}/characters")
    assert r.status_code == 404


def test_list_scene_chars_empty(sc_client):
    client, db = sc_client
    sid = _scene(db)
    r = client.get(f"/api/db/scenes/{sid}/characters")
    assert r.status_code == 200
    assert r.get_json()["characters"] == []


def test_list_scene_chars_returns_added(sc_client):
    client, db = sc_client
    sid = _scene(db)
    cid = _char(db)
    client.post(f"/api/db/scenes/{sid}/characters", json={"character_id": cid})
    r = client.get(f"/api/db/scenes/{sid}/characters")
    assert r.status_code == 200
    chars = r.get_json()["characters"]
    assert any(c["id"] == cid for c in chars)


def test_add_char_to_scene_scene_not_found(sc_client):
    client, db = sc_client
    cid = _char(db)
    r = client.post(
        f"/api/db/scenes/{new_id()}/characters",
        json={"character_id": cid},
    )
    assert r.status_code == 404


def test_add_char_to_scene_missing_char_id(sc_client):
    client, db = sc_client
    sid = _scene(db)
    r = client.post(f"/api/db/scenes/{sid}/characters", json={})
    assert r.status_code == 400


def test_add_char_to_scene_char_not_found(sc_client):
    client, db = sc_client
    sid = _scene(db)
    r = client.post(
        f"/api/db/scenes/{sid}/characters",
        json={"character_id": new_id()},
    )
    assert r.status_code == 404


def test_add_char_to_scene_201(sc_client):
    client, db = sc_client
    sid = _scene(db)
    cid = _char(db)
    r = client.post(f"/api/db/scenes/{sid}/characters", json={"character_id": cid})
    assert r.status_code == 201


def test_add_char_to_scene_conflict_409(sc_client):
    client, db = sc_client
    sid = _scene(db)
    cid = _char(db)
    client.post(f"/api/db/scenes/{sid}/characters", json={"character_id": cid})
    r = client.post(f"/api/db/scenes/{sid}/characters", json={"character_id": cid})
    assert r.status_code == 409


def test_update_scene_char_role_missing_role(sc_client):
    client, db = sc_client
    sid = _scene(db)
    cid = _char(db)
    client.post(f"/api/db/scenes/{sid}/characters", json={"character_id": cid})
    r = client.patch(f"/api/db/scenes/{sid}/characters/{cid}", json={})
    assert r.status_code == 400


def test_update_scene_char_role_not_found(sc_client):
    client, db = sc_client
    sid = _scene(db)
    r = client.patch(
        f"/api/db/scenes/{sid}/characters/{new_id()}",
        json={"role": "antagonist"},
    )
    assert r.status_code == 404


def test_update_scene_char_role_200(sc_client):
    client, db = sc_client
    sid = _scene(db)
    cid = _char(db)
    client.post(
        f"/api/db/scenes/{sid}/characters",
        json={"character_id": cid, "role": "protagonist"},
    )
    r = client.patch(
        f"/api/db/scenes/{sid}/characters/{cid}",
        json={"role": "antagonist"},
    )
    assert r.status_code == 200


def test_remove_char_from_scene_204(sc_client):
    client, db = sc_client
    sid = _scene(db)
    cid = _char(db)
    client.post(f"/api/db/scenes/{sid}/characters", json={"character_id": cid})
    r = client.delete(f"/api/db/scenes/{sid}/characters/{cid}")
    assert r.status_code == 204


def test_remove_char_from_scene_not_found(sc_client):
    client, db = sc_client
    sid = _scene(db)
    r = client.delete(f"/api/db/scenes/{sid}/characters/{new_id()}")
    assert r.status_code == 404
