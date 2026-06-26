"""
Contract test (father-authored acceptance) — WI-13.

Il worker Efesto deve far passare questi test creando
`app/calliope_shell/characters_db_routes.py` con:

    def register_characters_db_routes(app, *, db_path: str) -> None

che espone:

    GET  /api/db/characters          -> 200 + {"characters": [...]}
    POST /api/db/characters          -> 201 + {"id": "<uuid>"}
      body JSON: {"name": str, "kind"?: str}   (kind default "npc")
    GET  /api/db/characters/<id>     -> 200 + record | 404

Usa SOLO:
  app.db.characters.list_characters(conn) -> List[Mapping]
  app.db.characters.add_character(conn, *, name, kind) -> str (id)
  app.db.characters.get_character(conn, character_id) -> Mapping | None

NON modificare le assertion: sono il contratto di accettazione.
"""
import sys
from pathlib import Path

import pytest
from flask import Flask

from app.db import get_db, init_schema

sys.path.insert(0, str(Path(__file__).parents[2]))

try:
    from app.calliope_shell.characters_db_routes import register_characters_db_routes

    _MODULE_MISSING = False
except ImportError:
    _MODULE_MISSING = True


@pytest.fixture(autouse=True)
def require_module():
    if _MODULE_MISSING:
        pytest.fail(
            "app/calliope_shell/characters_db_routes.py mancante — "
            "implementare register_characters_db_routes con GET+POST /api/db/characters"
        )


@pytest.fixture
def client(tmp_path):
    p = tmp_path / "test.db"
    conn = get_db(p)
    init_schema(conn)
    conn.close()
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_characters_db_routes(app, db_path=str(p))
    return app.test_client()


# --- WI-13: characters DB CRUD ----------------------------------------------

def test_list_characters_empty(client):
    r = client.get("/api/db/characters")
    assert r.status_code == 200
    data = r.get_json()
    assert "characters" in data
    assert data["characters"] == []


def test_add_character_returns_201_with_id(client):
    r = client.post("/api/db/characters", json={"name": "Zara"})
    assert r.status_code == 201
    body = r.get_json()
    assert "id" in body
    assert isinstance(body["id"], str)
    assert len(body["id"]) > 0


def test_add_character_appears_in_list(client):
    char_id = client.post("/api/db/characters", json={"name": "Kira"}).get_json()["id"]
    lst = client.get("/api/db/characters").get_json()["characters"]
    ids = [ch["id"] for ch in lst]
    assert char_id in ids


def test_add_character_with_kind(client):
    r = client.post("/api/db/characters", json={"name": "Mira", "kind": "player"})
    assert r.status_code == 201
    char_id = r.get_json()["id"]
    detail = client.get(f"/api/db/characters/{char_id}").get_json()
    assert detail["kind"] == "player"


def test_get_character_detail(client):
    char_id = client.post("/api/db/characters", json={"name": "Reo"}).get_json()["id"]
    r = client.get(f"/api/db/characters/{char_id}")
    assert r.status_code == 200
    data = r.get_json()
    assert data["id"] == char_id
    assert data["name"] == "Reo"


def test_get_character_not_found_404(client):
    r = client.get("/api/db/characters/id-inesistente")
    assert r.status_code == 404


def test_add_character_missing_name_400(client):
    r = client.post("/api/db/characters", json={"kind": "npc"})
    assert r.status_code == 400


# --- PATCH /api/db/characters/<char_id> -------------------------------------

def test_patch_character_name_200(client):
    char_id = client.post("/api/db/characters", json={"name": "Vecchio"}).get_json()["id"]
    r = client.patch(f"/api/db/characters/{char_id}", json={"name": "Nuovo"})
    assert r.status_code == 200
    assert r.get_json() == {}


def test_patch_character_kind_200(client):
    char_id = client.post("/api/db/characters", json={"name": "K", "kind": "npc"}).get_json()["id"]
    r = client.patch(f"/api/db/characters/{char_id}", json={"kind": "player"})
    assert r.status_code == 200


def test_patch_character_empty_body_400(client):
    char_id = client.post("/api/db/characters", json={"name": "X"}).get_json()["id"]
    r = client.patch(f"/api/db/characters/{char_id}", json={})
    assert r.status_code == 400


def test_patch_character_invalid_kind_400(client):
    char_id = client.post("/api/db/characters", json={"name": "Y"}).get_json()["id"]
    r = client.patch(f"/api/db/characters/{char_id}", json={"kind": "villain"})
    assert r.status_code == 400


def test_patch_character_not_found_404(client):
    r = client.patch("/api/db/characters/nonexistent-id", json={"name": "Z"})
    assert r.status_code == 404


def test_patch_character_image_path_200(client):
    """PATCH image_path → 200, GET detail restituisce image_path aggiornato."""
    char_id = client.post("/api/db/characters", json={"name": "ImgChar"}).get_json()["id"]
    r = client.patch(f"/api/db/characters/{char_id}", json={"image_path": "/static/avatars/test.png"})
    assert r.status_code == 200
    data = client.get(f"/api/db/characters/{char_id}").get_json()
    char = data.get("character") or data
    assert char.get("image_path") == "/static/avatars/test.png"


def test_patch_character_image_path_null_clears(client):
    """PATCH image_path=null rimuove il path."""
    char_id = client.post("/api/db/characters", json={"name": "ImgChar2"}).get_json()["id"]
    client.patch(f"/api/db/characters/{char_id}", json={"image_path": "/some/path.png"})
    r = client.patch(f"/api/db/characters/{char_id}", json={"image_path": None})
    assert r.status_code == 200
    data = client.get(f"/api/db/characters/{char_id}").get_json()
    char = data.get("character") or data
    assert char.get("image_path") is None


# --- DELETE /api/db/characters/<char_id> ------------------------------------

def test_delete_character_204(client):
    char_id = client.post("/api/db/characters", json={"name": "ToDelete"}).get_json()["id"]
    r = client.delete(f"/api/db/characters/{char_id}")
    assert r.status_code == 204
    assert r.data == b""


def test_delete_character_not_found_404(client):
    r = client.delete("/api/db/characters/nonexistent-id")
    assert r.status_code == 404


def test_delete_character_removes_from_list(client):
    char_id = client.post("/api/db/characters", json={"name": "Gone"}).get_json()["id"]
    client.delete(f"/api/db/characters/{char_id}")
    ids = [c["id"] for c in client.get("/api/db/characters").get_json()["characters"]]
    assert char_id not in ids


# --- GET /api/db/characters?name= -------------------------------------------

def test_list_characters_name_filter_exact(client):
    client.post("/api/db/characters", json={"name": "Aurora"})
    client.post("/api/db/characters", json={"name": "Kael"})
    r = client.get("/api/db/characters?name=Aurora")
    assert r.status_code == 200
    chars = r.get_json()["characters"]
    assert len(chars) == 1
    assert chars[0]["name"] == "Aurora"


def test_list_characters_name_filter_case_insensitive(client):
    client.post("/api/db/characters", json={"name": "Borea"})
    r = client.get("/api/db/characters?name=borea")
    chars = r.get_json()["characters"]
    assert len(chars) == 1


def test_list_characters_name_filter_no_match(client):
    client.post("/api/db/characters", json={"name": "Zelda"})
    r = client.get("/api/db/characters?name=nonexistent")
    assert r.get_json()["characters"] == []


def test_add_character_invalid_kind_400(client):
    r = client.post("/api/db/characters", json={"name": "X", "kind": "villain"})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_add_character_name_too_long_400(client):
    long_name = "A" * 256
    r = client.post("/api/db/characters", json={"name": long_name})
    assert r.status_code == 400
    assert "error" in r.get_json()


# --- GET /api/db/characters/<char_id>/scenes ---------------------------------

def test_list_scenes_for_character_empty(client, tmp_path):
    """Personaggio senza scene → lista vuota 200."""
    char_id = client.post("/api/db/characters", json={"name": "Solo"}).get_json()["id"]
    r = client.get(f"/api/db/characters/{char_id}/scenes")
    assert r.status_code == 200
    assert r.get_json()["scenes"] == []


def test_list_scenes_for_character_with_scene(tmp_path):
    """Dopo POST /api/db/scenes/<id>/characters, la scena compare nella lista scene del char."""
    from app.db import get_db, init_schema
    from app.calliope_shell.scenes_db_routes import register_scenes_db_routes

    p = tmp_path / "all.db"
    conn = get_db(str(p))
    init_schema(conn)
    conn.close()

    app2 = Flask(__name__)
    app2.config["TESTING"] = True
    register_characters_db_routes(app2, db_path=str(p))
    register_scenes_db_routes(app2, db_path=str(p))
    c2 = app2.test_client()

    char_id = c2.post("/api/db/characters", json={"name": "Kira"}).get_json()["id"]
    scene_id = c2.post("/api/db/scenes", json={"title": "Notte"}).get_json()["id"]
    c2.post(f"/api/db/scenes/{scene_id}/characters",
            json={"character_id": char_id, "role": "player"})

    r = c2.get(f"/api/db/characters/{char_id}/scenes")
    assert r.status_code == 200
    scenes = r.get_json()["scenes"]
    assert any(s["id"] == scene_id for s in scenes)
