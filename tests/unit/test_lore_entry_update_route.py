"""
Contract test (father-authored acceptance) — WI-60.

Il worker Efesto deve far passare questi test modificando
`app/calliope_shell/lore_routes.py`:

1. Aggiungere parametro store_path a register_lore_routes (vedi WI-34):
       def register_lore_routes(app, *, store_path=None)
   e passarlo a LoreStore() in OGNI route handler:
       store = LoreStore(path=store_path)

2. Verificare che PUT /api/lore/entries/<entry_id> funzioni correttamente:
   - body JSON: uno o piu' campi opzionali tra title, content, category
   - -> 200 + entry aggiornata come dict
   - -> 404 se entry_id non esiste

NON modificare le assertion: sono il contratto di accettazione.
"""
import pytest
from flask import Flask

from app.calliope_shell.lore_routes import register_lore_routes


@pytest.fixture
def client(tmp_path):
    store_file = tmp_path / "lore_test.json"
    app = Flask(__name__)
    app.config["TESTING"] = True
    # store_path injection: se register_lore_routes non lo accetta -> TypeError -> RED
    register_lore_routes(app, store_path=store_file)
    return app.test_client()


def _create(client, title, category="other", content="testo iniziale"):
    return client.post(
        "/api/lore/entries",
        json={"title": title, "category": category, "content": content},
    ).get_json()["id"]


# --- WI-60: PUT /api/lore/entries/<id> update --------------------------------

def test_put_updates_title(client):
    eid = _create(client, "Titolo Vecchio")
    r = client.put(f"/api/lore/entries/{eid}", json={"title": "Titolo Nuovo"})
    assert r.status_code == 200
    assert r.get_json()["title"] == "Titolo Nuovo"


def test_put_preserves_unupdated_category(client):
    eid = _create(client, "Stabile", category="places")
    r = client.put(f"/api/lore/entries/{eid}", json={"title": "Cambiato"})
    assert r.get_json()["category"] == "places"


def test_put_updates_content(client):
    eid = _create(client, "Entry", content="vecchio")
    r = client.put(f"/api/lore/entries/{eid}", json={"content": "nuovo contenuto"})
    assert r.status_code == 200
    assert r.get_json()["content"] == "nuovo contenuto"


def test_put_not_found_returns_404(client):
    r = client.put("/api/lore/entries/entry-inesistente", json={"title": "X"})
    assert r.status_code == 404


# --- GAP-17: DELETE /api/lore/entries/<id> --------------------------------

def test_delete_entry(client):
    eid = _create(client, "Da Eliminare")
    r = client.delete(f"/api/lore/entries/{eid}")
    assert r.status_code == 200
    assert r.get_json()["deleted"] is True


def test_delete_removes_from_list(client):
    eid = _create(client, "Temporanea")
    client.delete(f"/api/lore/entries/{eid}")
    entries = client.get("/api/lore/entries").get_json()["entries"]
    assert all(e["id"] != eid for e in entries)


def test_delete_not_found_returns_404(client):
    r = client.delete("/api/lore/entries/non-esistente")
    assert r.status_code == 404


# --- GAP-18: GET /api/lore/entries/<id> --------------------------------

def test_get_entry_by_id(client):
    eid = _create(client, "Voce Singola", category="places", content="contenuto")
    r = client.get(f"/api/lore/entries/{eid}")
    assert r.status_code == 200
    body = r.get_json()
    assert body["id"] == eid
    assert body["title"] == "Voce Singola"
    assert body["category"] == "places"


def test_get_entry_not_found(client):
    r = client.get("/api/lore/entries/inesistente")
    assert r.status_code == 404
