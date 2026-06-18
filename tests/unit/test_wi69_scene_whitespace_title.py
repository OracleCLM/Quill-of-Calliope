"""
Contract test (father-authored acceptance) — WI-69.

La creazione scena valida già title assente/vuoto (-> 400), ma un title
composto SOLO da whitespace ("   ") passa il check `if not title` ed entra in
DB con titolo vuoto-effettivo. Il worker Efesto deve normalizzare con `.strip()`
nell'handler POST /api/db/scenes in `app/calliope_shell/scenes_db_routes.py`:

    POST /api/db/scenes
      body {"title": "   "}  (solo spazi)  -> 400 {"error": ...}
      (comportamento invariato: title valido -> 201; title assente/"" -> 400)

Usa SOLO: from app.db import get_db, init_schema.
NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema
from app.calliope_shell.scenes_db_routes import register_scenes_db_routes


@pytest.fixture
def client(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    conn.close()
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=str(p))
    return app.test_client()


# --- WI-69: title whitespace-only -> 400 ------------------------------------

def test_create_scene_whitespace_only_title_rejected(client):
    r = client.post("/api/db/scenes", json={"title": "   "})
    assert r.status_code == 400


def test_create_scene_valid_title_still_ok(client):
    r = client.post("/api/db/scenes", json={"title": "A Real Scene"})
    assert r.status_code == 201
