"""
Contract test (father-authored acceptance) — WI-62.

Il worker Efesto deve far passare questi test modificando
`app/calliope_shell/lore_routes.py`:

    Aggiungere parametro store_path a register_lore_routes (vedi WI-34):
        def register_lore_routes(app, *, store_path=None)

    GET /api/lore/categories deve rispondere 200 con la lista delle categorie
    valide anche quando store_path e' iniettato.
    Categorie attese (da LORE_CATEGORIES in lore_kb.py):
        world_setting, places, characters_events, mechanics_magic, other

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


# --- WI-62: GET /api/lore/categories -----------------------------------------

def test_categories_returns_200(client):
    r = client.get("/api/lore/categories")
    assert r.status_code == 200


def test_categories_list_is_not_empty(client):
    cats = client.get("/api/lore/categories").get_json()["categories"]
    assert isinstance(cats, list) and len(cats) > 0


def test_categories_includes_places(client):
    cats = client.get("/api/lore/categories").get_json()["categories"]
    assert "places" in cats


def test_categories_includes_characters_events(client):
    cats = client.get("/api/lore/categories").get_json()["categories"]
    assert "characters_events" in cats


def test_categories_includes_world_setting(client):
    cats = client.get("/api/lore/categories").get_json()["categories"]
    assert "world_setting" in cats
