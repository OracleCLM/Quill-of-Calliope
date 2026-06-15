"""
Contract test (father-authored acceptance) — WI-64.

Il worker Efesto deve far passare questi test completando WI-31 E aggiungendo
supporto al campo opzionale `location`:

1. In `app/db/scenes.py`:
       create_scene(conn, title, *, location=None) -> str
       - title obbligatorio (raise ValueError se vuoto)
       - location opzionale, salvato in scenes.location (NULL se non fornito)
       - ritorna UUID della scena creata

2. Route POST /api/db/scenes in `app/calliope_shell/scenes_db_routes.py`:
       body JSON: {"title": str, "location"?: str}
       -> 201 + {"id": str, "title": str, "location": str | null}
   GET /api/db/scenes/<id> deve includere "location" nel dict "scene".

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


# --- WI-64: POST /api/db/scenes con location ---------------------------------

def test_create_with_location_returns_201(client):
    r = client.post("/api/db/scenes", json={"title": "Foresta", "location": "Bosco Oscuro"})
    assert r.status_code == 201


def test_create_with_location_in_response(client):
    r = client.post("/api/db/scenes", json={"title": "Foresta", "location": "Bosco Oscuro"})
    assert r.get_json().get("location") == "Bosco Oscuro"


def test_create_with_location_persisted_in_detail(client):
    scene_id = client.post(
        "/api/db/scenes", json={"title": "Tempio", "location": "Monte Sacro"}
    ).get_json()["id"]
    detail = client.get(f"/api/db/scenes/{scene_id}").get_json()
    assert detail["scene"]["location"] == "Monte Sacro"


def test_create_without_location_defaults_to_null(client):
    scene_id = client.post(
        "/api/db/scenes", json={"title": "Senza Location"}
    ).get_json()["id"]
    detail = client.get(f"/api/db/scenes/{scene_id}").get_json()
    assert detail["scene"]["location"] is None
