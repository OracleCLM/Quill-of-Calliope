"""GAP-71: test per GET /arcs/<id>/scenes e test unici GET/DELETE arco.
GET/DELETE base coperta da test_arc_detail_route.py (acceptance padre).
"""

import sys
from pathlib import Path

import pytest
from flask import Flask

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.arcs_db_routes import register_arcs_db_routes
from app.db import get_db, init_schema


@pytest.fixture
def client(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    conn.close()
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_arcs_db_routes(app, db_path=str(p))
    return app.test_client()


def _create(c, title="Arc Test"):
    r = c.post("/api/db/arcs", json={"title": title})
    return r.get_json()["id"]


# ── GET /api/db/arcs/<arc_id> — solo test unici (200/404 base in test_arc_detail_route.py)


def test_get_arc_returns_title(client):
    arc_id = _create(client, "Arc Visibile")
    data = client.get(f"/api/db/arcs/{arc_id}").get_json()
    assert data["title"] == "Arc Visibile"


# ── DELETE /api/db/arcs/<arc_id> — solo test unici ────────────────────────────


def test_delete_arc_second_call_returns_404(client):
    arc_id = _create(client, "Arc Unico")
    client.delete(f"/api/db/arcs/{arc_id}")
    r = client.delete(f"/api/db/arcs/{arc_id}")
    assert r.status_code == 404


# ── GET /api/db/arcs/<arc_id>/scenes ─────────────────────────────────────────


def test_arc_scenes_returns_200(client):
    arc_id = _create(client, "Arc con Scene")
    r = client.get(f"/api/db/arcs/{arc_id}/scenes")
    assert r.status_code == 200


def test_arc_scenes_empty_on_new_arc(client):
    arc_id = _create(client, "Arc Vuoto")
    data = client.get(f"/api/db/arcs/{arc_id}/scenes").get_json()
    assert data["scenes"] == []
    assert data["arc_id"] == arc_id


def test_arc_scenes_not_found_returns_404(client):
    r = client.get("/api/db/arcs/arc-inesistente/scenes")
    assert r.status_code == 404
