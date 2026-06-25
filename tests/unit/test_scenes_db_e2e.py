"""
E2E HTTP tests per il flusso compose FE → BE:
  GET  /api/db/scenes            → lista con message_count
  POST /api/db/scenes/<id>/messages → 201 + id
  GET  /api/db/scenes/<id>       → messaggio nel thread

Usa Flask minimale con register_scenes_db_routes(app, db_path=tmp_path)
così il DB è isolato per ogni test.
"""
from __future__ import annotations

import sys
from pathlib import Path

from flask import Flask

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db import get_db, init_schema, new_id
from app.calliope_shell.scenes_db_routes import register_scenes_db_routes


def _make_app(db_path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=db_path)
    return app


def _seed_scene(conn, title="Scena E2E", location="Foresta"):
    scene_id = new_id()
    conn.execute(
        "INSERT INTO scenes (id, title, location) VALUES (?, ?, ?)",
        (scene_id, title, location),
    )
    conn.commit()
    return scene_id


# ── GET /api/db/scenes → message_count ───────────────────────────────────────

def test_list_scenes_e2e_message_count(tmp_path):
    db_path = tmp_path / "e2e.db"
    conn = get_db(db_path)
    init_schema(conn)
    scene_id = _seed_scene(conn, title="Scena con messaggi")
    conn.execute(
        "INSERT INTO messages (id, scene_id, author_name, content_original, position_order, source, ts)"
        " VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
        (new_id(), scene_id, "Alice", "ciao mondo", 0, "manual"),
    )
    conn.execute(
        "INSERT INTO messages (id, scene_id, author_name, content_original, position_order, source, ts)"
        " VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
        (new_id(), scene_id, "Bob", "risposta", 1, "manual"),
    )
    conn.commit()
    conn.close()

    app = _make_app(db_path)
    with app.test_client() as c:
        r = c.get("/api/db/scenes")
    assert r.status_code == 200
    data = r.get_json()
    scenes = data["scenes"]
    assert len(scenes) == 1
    assert scenes[0]["message_count"] == 2
    assert scenes[0]["title"] == "Scena con messaggi"


# ── POST /api/db/scenes/<id>/messages → 201 ──────────────────────────────────

def test_append_message_returns_201_and_id(tmp_path):
    db_path = tmp_path / "e2e.db"
    conn = get_db(db_path)
    init_schema(conn)
    scene_id = _seed_scene(conn)
    conn.close()

    app = _make_app(db_path)
    with app.test_client() as c:
        r = c.post(
            f"/api/db/scenes/{scene_id}/messages",
            json={"author_name": "Narratore", "content_original": "La storia inizia."},
        )
    assert r.status_code == 201
    data = r.get_json()
    assert "id" in data
    assert data["id"]


def test_append_message_400_missing_author(tmp_path):
    db_path = tmp_path / "e2e.db"
    conn = get_db(db_path)
    init_schema(conn)
    scene_id = _seed_scene(conn)
    conn.close()

    app = _make_app(db_path)
    with app.test_client() as c:
        r = c.post(
            f"/api/db/scenes/{scene_id}/messages",
            json={"content_original": "testo senza autore"},
        )
    assert r.status_code == 400


# ── GET /api/db/scenes/<id> → messaggio nel thread ───────────────────────────

def test_get_scene_detail_includes_appended_message(tmp_path):
    db_path = tmp_path / "e2e.db"
    conn = get_db(db_path)
    init_schema(conn)
    scene_id = _seed_scene(conn, title="Scena narrata")
    conn.close()

    app = _make_app(db_path)
    with app.test_client() as c:
        post_r = c.post(
            f"/api/db/scenes/{scene_id}/messages",
            json={"author_name": "Narratore", "content_original": "La nebbia avvolge il bosco."},
        )
        assert post_r.status_code == 201

        get_r = c.get(f"/api/db/scenes/{scene_id}")
    assert get_r.status_code == 200
    data = get_r.get_json()
    assert data["scene"]["title"] == "Scena narrata"
    messages = data["messages"]
    assert len(messages) == 1
    assert messages[0]["author_name"] == "Narratore"
    assert messages[0]["content_original"] == "La nebbia avvolge il bosco."


def test_e2e_full_flow_scene_list_updates_after_append(tmp_path):
    """message_count nella lista si aggiorna dopo POST /messages."""
    db_path = tmp_path / "e2e.db"
    conn = get_db(db_path)
    init_schema(conn)
    scene_id = _seed_scene(conn, title="Flusso completo")
    conn.close()

    app = _make_app(db_path)
    with app.test_client() as c:
        r0 = c.get("/api/db/scenes")
        assert r0.get_json()["scenes"][0]["message_count"] == 0

        c.post(
            f"/api/db/scenes/{scene_id}/messages",
            json={"author_name": "Alice", "content_original": "primo msg"},
        )
        c.post(
            f"/api/db/scenes/{scene_id}/messages",
            json={"author_name": "Bob", "content_original": "secondo msg"},
        )

        r1 = c.get("/api/db/scenes")
    assert r1.get_json()["scenes"][0]["message_count"] == 2
