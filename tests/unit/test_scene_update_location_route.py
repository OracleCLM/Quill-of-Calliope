"""
Contract test (father-authored acceptance) — WI-65.

Il worker Efesto deve far passare questi test completando WI-32 E aggiungendo
supporto al campo opzionale `location` nel PATCH:

1. In `app/db/scenes.py`:
       update_scene(conn, scene_id, *, title=None, location=None) -> bool
       (estende o sostituisce update_scene_title di WI-32)
       - aggiorna solo i campi non-None
       - ritorna True se aggiornato, False se scene non esiste
       - raise ValueError se title e' fornito ma stringa vuota

2. Route PATCH /api/db/scenes/<scene_id> in `app/calliope_shell/scenes_db_routes.py`:
       body JSON: {"title"?: str, "location"?: str}
       -> 200 se almeno un campo valido fornito
       -> 400 se body JSON vuoto (nessun campo aggiornabile)
       -> 404 se scene_id non esiste

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.db import get_db, init_schema, new_id
from app.calliope_shell.scenes_db_routes import register_scenes_db_routes


@pytest.fixture
def seeded(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    scene_id = new_id()
    conn.execute(
        "INSERT INTO scenes (id, title, location) VALUES (?, ?, ?)",
        (scene_id, "Scena Originale", "Villaggio"),
    )
    conn.commit()
    conn.close()
    return {"path": str(p), "scene_id": scene_id}


@pytest.fixture
def client(seeded):
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_scenes_db_routes(app, db_path=seeded["path"])
    return app.test_client(), seeded


# --- WI-65: PATCH /api/db/scenes/<id> con location ---------------------------

def test_patch_location_returns_200(client):
    c, s = client
    r = c.patch(f"/api/db/scenes/{s['scene_id']}", json={"location": "Castello"})
    assert r.status_code == 200


def test_patch_location_reflected_in_detail(client):
    c, s = client
    c.patch(f"/api/db/scenes/{s['scene_id']}", json={"location": "Foresta Arcana"})
    detail = c.get(f"/api/db/scenes/{s['scene_id']}").get_json()
    assert detail["scene"]["location"] == "Foresta Arcana"


def test_patch_location_does_not_overwrite_title(client):
    c, s = client
    c.patch(f"/api/db/scenes/{s['scene_id']}", json={"location": "Nuova Location"})
    detail = c.get(f"/api/db/scenes/{s['scene_id']}").get_json()
    assert detail["scene"]["title"] == "Scena Originale"


def test_patch_empty_body_returns_400(client):
    c, s = client
    r = c.patch(f"/api/db/scenes/{s['scene_id']}", json={})
    assert r.status_code == 400


def test_patch_location_not_found_returns_404(client):
    c, _ = client
    r = c.patch("/api/db/scenes/scena-inesistente", json={"location": "X"})
    assert r.status_code == 404
