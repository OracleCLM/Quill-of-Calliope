"""
Contract test (father-authored acceptance) — WI-47.

Il worker Efesto deve far passare questi test modificando
`app/calliope_shell/characters_db_routes.py`:

1. Route POST /api/db/characters:
       Leggere il campo opzionale "card_json" dal body e passarlo a:
         db_chars.add_character(conn, name=name, kind=kind, card_json=card_json)
       card_json e' una stringa JSON che codifica la scheda personaggio
       (nessuna validazione struttura richiesta — e' opaco per la route).

2. Route PATCH /api/db/characters/<char_id> (creata in WI-23):
       Leggere il campo opzionale "card_json" dal body e passarlo a:
         db_chars.update_character(conn, char_id, card_json=card_json)

3. Route GET /api/db/characters/<char_id> (gia' implementata):
       La route usa db_chars.get_character che fa SELECT * -> restituisce
       card_json automaticamente. Nessuna modifica alla GET.

Usa SOLO: parametro card_json gia' accettato da add_character (app/db/characters.py:27)
  e update_character (app/db/characters.py:136).

NON modificare le assertion: sono il contratto di accettazione.
"""
import json

import pytest
from flask import Flask

from app.db import get_db, init_schema
from app.calliope_shell.characters_db_routes import register_characters_db_routes


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


CARD = json.dumps({"backstory": "Ex-samurai", "traits": ["stoico", "leale"]})


# --- WI-47: card_json in POST /api/db/characters ----------------------------

def test_create_character_with_card_json_stored(client):
    cid = client.post(
        "/api/db/characters",
        json={"name": "Takeshi", "kind": "npc", "card_json": CARD},
    ).get_json()["id"]
    data = client.get(f"/api/db/characters/{cid}").get_json()
    assert data["card_json"] == CARD


def test_create_character_without_card_json_stores_null(client):
    cid = client.post(
        "/api/db/characters", json={"name": "Mira", "kind": "npc"}
    ).get_json()["id"]
    data = client.get(f"/api/db/characters/{cid}").get_json()
    assert data["card_json"] is None


# --- WI-47: card_json in PATCH /api/db/characters/<id> ----------------------

def test_update_card_json_stored(client):
    cid = client.post(
        "/api/db/characters", json={"name": "Ryo", "kind": "player"}
    ).get_json()["id"]
    new_card = json.dumps({"backstory": "Ronin", "traits": ["solitario"]})
    client.patch(f"/api/db/characters/{cid}", json={"card_json": new_card})
    data = client.get(f"/api/db/characters/{cid}").get_json()
    assert data["card_json"] == new_card


def test_update_card_json_does_not_overwrite_name(client):
    cid = client.post(
        "/api/db/characters", json={"name": "Luna", "kind": "npc"}
    ).get_json()["id"]
    client.patch(f"/api/db/characters/{cid}", json={"card_json": CARD})
    data = client.get(f"/api/db/characters/{cid}").get_json()
    assert data["name"] == "Luna"
    assert data["card_json"] == CARD
