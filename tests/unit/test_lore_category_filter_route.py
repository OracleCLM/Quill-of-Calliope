"""
Contract test (father-authored acceptance) — WI-61.

Il worker Efesto deve far passare questi test modificando
`app/calliope_shell/lore_routes.py`:

1. Aggiungere parametro store_path a register_lore_routes (vedi WI-34):
       def register_lore_routes(app, *, store_path=None)
   e passarlo a LoreStore() in OGNI route handler.

2. Verificare che GET /api/lore/entries?category=X filtri correttamente:
   - ?category=<cat>  -> solo entry della categoria specificata
   - senza ?category  -> tutte le entry (nessun filtro)
   - ?category non esistente -> lista vuota (non 404)

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


def _seed(client):
    client.post("/api/lore/entries", json={"title": "Yokai Forest", "category": "places"})
    client.post("/api/lore/entries", json={"title": "Aurora", "category": "characters_events"})
    client.post("/api/lore/entries", json={"title": "Spirit World", "category": "places"})


# --- WI-61: GET /api/lore/entries?category=X ---------------------------------

def test_filter_returns_only_matching_category(client):
    _seed(client)
    r = client.get("/api/lore/entries?category=places")
    assert r.status_code == 200
    titles = [e["title"] for e in r.get_json()["entries"]]
    assert "Yokai Forest" in titles
    assert "Spirit World" in titles
    assert "Aurora" not in titles


def test_filter_excludes_other_categories(client):
    _seed(client)
    entries = client.get(
        "/api/lore/entries?category=characters_events"
    ).get_json()["entries"]
    assert len(entries) == 1
    assert entries[0]["title"] == "Aurora"


def test_filter_unknown_category_returns_empty_list(client):
    _seed(client)
    r = client.get("/api/lore/entries?category=categoria_inesistente")
    assert r.status_code == 200
    assert r.get_json()["entries"] == []


def test_no_filter_returns_all_entries(client):
    _seed(client)
    r = client.get("/api/lore/entries")
    assert r.status_code == 200
    assert len(r.get_json()["entries"]) == 3
