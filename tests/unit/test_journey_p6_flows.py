"""Journey test P6 — Given/When/Then a stato-risultante.

Blinda i flussi UI critici del redesign P6 confermati via Playwright round-2:
- GAP-1: /api/db/characters cablato in create_app (era 404)
- GAP-2/3: arc seed YAML→SQLite al boot (dropdown archi vuoto)
- FLOW-7: PATCH scene con arc_id — salva e si riflette in detail
- KIND-BADGE: GET /api/db/characters/<id> restituisce campo `kind`
"""
from __future__ import annotations

import pytest

from app.calliope_shell.server import create_app


@pytest.fixture(scope="module")
def client():
    app, _ = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── GAP-1: characters DB route ────────────────────────────────────────────────

class TestGap1CharactersDbRoute:
    """GIVEN l'app Flask avviata / WHEN GET /api/db/characters / THEN 200 + lista."""

    def test_route_returns_200(self, client):
        r = client.get("/api/db/characters")
        assert r.status_code == 200

    def test_response_has_characters_key(self, client):
        data = client.get("/api/db/characters").get_json()
        assert "characters" in data

    def test_characters_is_a_list(self, client):
        data = client.get("/api/db/characters").get_json()
        assert isinstance(data["characters"], list)

    def test_at_least_one_character_loaded(self, client):
        """Verifica che la suite non giri su un DB vuoto — almeno 1 personaggio."""
        data = client.get("/api/db/characters").get_json()
        assert len(data["characters"]) >= 1, "DB personaggi sembra vuoto — seed mancante?"

    def test_character_detail_returns_kind_field(self, client):
        """GIVEN un personaggio esistente / WHEN GET /api/db/characters/<id> / THEN `kind` presente."""
        chars = client.get("/api/db/characters").get_json()["characters"]
        cid = chars[0]["id"]
        data = client.get(f"/api/db/characters/{cid}").get_json()
        char = data.get("character") or data
        assert "kind" in char, f"campo `kind` assente in GET /api/db/characters/{cid}"

    def test_character_scenes_endpoint_returns_200(self, client):
        """GIVEN un personaggio / WHEN GET /api/db/characters/<id>/scenes / THEN 200."""
        chars = client.get("/api/db/characters").get_json()["characters"]
        cid = chars[0]["id"]
        r = client.get(f"/api/db/characters/{cid}/scenes")
        assert r.status_code == 200


# ── GAP-2/3: arc seed ─────────────────────────────────────────────────────────

class TestGap23ArcSeed:
    """GIVEN create_app() eseguita / WHEN GET /api/db/arcs / THEN ≥6 archi seedati da YAML."""

    def test_arcs_endpoint_returns_200(self, client):
        r = client.get("/api/db/arcs")
        assert r.status_code == 200

    def test_arcs_response_has_arcs_key(self, client):
        data = client.get("/api/db/arcs").get_json()
        assert "arcs" in data

    def test_at_least_six_arcs_seeded(self, client):
        """YAML ha 6 archi; il seed li porta in SQLite al boot."""
        data = client.get("/api/db/arcs").get_json()
        assert len(data["arcs"]) >= 6, (
            f"Solo {len(data['arcs'])} archi nel DB — seed YAML→SQLite non eseguito?"
        )

    def test_each_arc_has_id_and_title(self, client):
        arcs = client.get("/api/db/arcs").get_json()["arcs"]
        for a in arcs:
            assert "id" in a, f"arco senza `id`: {a}"
            assert "title" in a, f"arco senza `title`: {a}"


# ── FLOW-7: arc assign via PATCH scene ────────────────────────────────────────

class TestFlow7ArcAssign:
    """GIVEN scena + archi nel DB / WHEN PATCH arc_id / THEN arc_id riflesso in GET detail."""

    @pytest.fixture
    def scene_id(self, client):
        """Crea una scena temporanea e la restituisce; cleanup implicito (scena orfana nel DB)."""
        r = client.post(
            "/api/db/scenes",
            json={"title": "journey-test-arc-assign"},
        )
        assert r.status_code in (200, 201)
        return r.get_json()["id"]

    def test_patch_arc_id_returns_200(self, client, scene_id):
        arcs = client.get("/api/db/arcs").get_json()["arcs"]
        arc_id = arcs[0]["id"]
        r = client.patch(f"/api/db/scenes/{scene_id}", json={"title": "journey-test-arc-assign", "arc_id": arc_id})
        assert r.status_code == 200

    def test_patch_arc_id_reflected_in_detail(self, client, scene_id):
        arcs = client.get("/api/db/arcs").get_json()["arcs"]
        arc_id = arcs[0]["id"]
        client.patch(f"/api/db/scenes/{scene_id}", json={"title": "journey-test-arc-assign", "arc_id": arc_id})
        detail = client.get(f"/api/db/scenes/{scene_id}").get_json()
        assert detail["scene"]["arc_id"] == arc_id

    def test_patch_arc_id_null_removes_arc(self, client, scene_id):
        arcs = client.get("/api/db/arcs").get_json()["arcs"]
        arc_id = arcs[0]["id"]
        client.patch(f"/api/db/scenes/{scene_id}", json={"title": "journey-test-arc-assign", "arc_id": arc_id})
        client.patch(f"/api/db/scenes/{scene_id}", json={"title": "journey-test-arc-assign", "arc_id": None})
        detail = client.get(f"/api/db/scenes/{scene_id}").get_json()
        assert detail["scene"]["arc_id"] is None

    def test_arc_filter_returns_scene_after_assign(self, client, scene_id):
        """WHEN arc assegnato / THEN la scena compare nel filtro GET /api/db/scenes?arc_id=X."""
        arcs = client.get("/api/db/arcs").get_json()["arcs"]
        arc_id = arcs[0]["id"]
        client.patch(f"/api/db/scenes/{scene_id}", json={"title": "journey-test-arc-assign", "arc_id": arc_id})
        scenes = client.get(f"/api/db/scenes?arc_id={arc_id}").get_json().get("scenes", [])
        ids = [s["id"] for s in scenes]
        assert scene_id in ids, f"scena {scene_id} non trovata nel filtro arc_id={arc_id}"
