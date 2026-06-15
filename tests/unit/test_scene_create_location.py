"""
Contract test (father-authored acceptance) — WI-46.

Il worker Efesto deve far passare questi test modificando:

1. `app/db/scenes.py` — funzione create_scene (creata in WI-31):
       create_scene(conn: sqlite3.Connection, title: str, location: str = "") -> str
       - aggiungere parametro opzionale location (default "")
       - inserire location nella riga scenes(id, title, location)

2. Route in `app/calliope_shell/scenes_db_routes.py`
   POST /api/db/scenes (creata in WI-31):
       Leggere body.get("location", "") e passarlo a create_scene.

3. Verificare che GET /api/db/scenes/<id> restituisca location nel
   dizionario "scene".

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


# --- WI-46: campo location in create_scene ----------------------------------

def test_create_scene_without_location_returns_201(client):
    r = client.post("/api/db/scenes", json={"title": "La Cripta"})
    assert r.status_code == 201


def test_create_scene_with_location_stored(client):
    scene_id = client.post(
        "/api/db/scenes", json={"title": "Il Castello", "location": "Nord Montagne"}
    ).get_json()["id"]
    detail = client.get(f"/api/db/scenes/{scene_id}").get_json()
    assert detail["scene"]["location"] == "Nord Montagne"


def test_create_scene_location_defaults_to_empty(client):
    scene_id = client.post(
        "/api/db/scenes", json={"title": "Senza Luogo"}
    ).get_json()["id"]
    detail = client.get(f"/api/db/scenes/{scene_id}").get_json()
    # location puo' essere "" o None — entrambi accettabili come "vuoto"
    assert detail["scene"].get("location") in (None, "")


def test_create_scene_location_in_list(client):
    client.post(
        "/api/db/scenes", json={"title": "Rovine", "location": "Pianura del Sud"}
    )
    scenes = client.get("/api/db/scenes").get_json()["scenes"]
    match = next((sc for sc in scenes if sc["title"] == "Rovine"), None)
    assert match is not None
    assert match.get("location") == "Pianura del Sud"
