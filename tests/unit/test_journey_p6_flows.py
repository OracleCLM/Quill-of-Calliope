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


# ── FLOW-8: Salva summary come messaggio is_summary=1 (VISION Principio 3) ───

class TestFlow8SummaryInScene:
    """GIVEN scena con messaggi / WHEN POST summary con is_summary=1 / THEN messaggio verde nel thread."""

    @pytest.fixture
    def scene_with_msgs(self, client):
        """Crea una scena con 2 messaggi normali."""
        r = client.post("/api/db/scenes", json={"title": "test-summary-scene"})
        scene_id = r.get_json()["id"]
        client.post(f"/api/db/scenes/{scene_id}/messages",
                    json={"author_name": "Alice", "content_original": "Primo messaggio"})
        client.post(f"/api/db/scenes/{scene_id}/messages",
                    json={"author_name": "Bob", "content_original": "Secondo messaggio"})
        return scene_id

    def test_summary_message_saved_with_is_summary_flag(self, client, scene_with_msgs):
        """WHEN POST messaggio con is_summary=1 / THEN campo is_summary=1 in GET."""
        scene_id = scene_with_msgs
        r = client.post(f"/api/db/scenes/{scene_id}/messages", json={
            "author_name": "Sistema",
            "content_original": "Riassunto: Alice e Bob si sono incontrati.",
            "is_summary": 1,
            "source": "summary",
        })
        assert r.status_code == 201
        msgs = client.get(f"/api/db/scenes/{scene_id}").get_json()["messages"]
        summary_msgs = [m for m in msgs if m.get("is_summary") in (1, True)]
        assert len(summary_msgs) == 1
        assert "Riassunto" in summary_msgs[0]["content_original"]

    def test_summary_message_has_source_summary(self, client, scene_with_msgs):
        """WHEN POST is_summary con source='summary' / THEN source nel DB è 'summary'."""
        scene_id = scene_with_msgs
        client.post(f"/api/db/scenes/{scene_id}/messages", json={
            "author_name": "Sistema",
            "content_original": "Recap della sessione.",
            "is_summary": 1,
            "source": "summary",
        })
        msgs = client.get(f"/api/db/scenes/{scene_id}").get_json()["messages"]
        summary_msg = next((m for m in msgs if m.get("is_summary") in (1, True)), None)
        assert summary_msg is not None
        assert summary_msg.get("source") == "summary"


# ── FLOW-9: Characters griglia — GET /api/db/characters → kind badge ──────────

class TestFlow9CharactersGrid:
    """GIVEN personaggi nel DB / WHEN GET lista e dettaglio / THEN kind e stem presenti."""

    def test_characters_list_returns_stem_and_kind(self, client):
        """GIVEN almeno 1 personaggio / WHEN GET /api/db/characters / THEN stem+kind in ogni entry."""
        data = client.get("/api/db/characters").get_json()
        chars = data.get("characters", [])
        assert len(chars) >= 1, "DB personaggi vuoto"
        for c in chars:
            assert "id" in c, f"personaggio senza id: {c}"
            assert "name" in c, f"personaggio senza name: {c}"

    def test_character_detail_has_kind(self, client):
        """GIVEN personaggio esistente / WHEN GET dettaglio / THEN campo kind presente e valido."""
        chars = client.get("/api/db/characters").get_json()["characters"]
        cid = chars[0]["id"]
        data = client.get(f"/api/db/characters/{cid}").get_json()
        char = data.get("character") or data
        kind = char.get("kind")
        assert kind is not None, f"kind assente in GET /api/db/characters/{cid}"
        assert kind in ("player", "npc", "operator"), f"kind non valido: {kind!r}"

    def test_create_and_retrieve_character(self, client):
        """GIVEN POST nuovo personaggio / WHEN GET lista / THEN trovato per id."""
        r = client.post("/api/db/characters", json={"name": "TestChar-Journey9", "kind": "npc"})
        assert r.status_code == 201
        char_id = r.get_json()["id"]
        data = client.get(f"/api/db/characters/{char_id}").get_json()
        char = data.get("character") or data
        assert char["name"] == "TestChar-Journey9"
        assert char["kind"] == "npc"

    def test_patch_character_kind_reflected(self, client):
        """GIVEN personaggio npc / WHEN PATCH kind=player / THEN GET mostra player."""
        r = client.post("/api/db/characters", json={"name": "KindFlip-Journey9", "kind": "npc"})
        cid = r.get_json()["id"]
        client.patch(f"/api/db/characters/{cid}", json={"kind": "player"})
        data = client.get(f"/api/db/characters/{cid}").get_json()
        char = data.get("character") or data
        assert char["kind"] == "player"


# ── FLOW-10: Characters PATCH completo — nome + kind + image_path ─────────────

class TestFlow10CharacterPatchFull:
    """GIVEN personaggio nel DB / WHEN PATCH nome+kind+image / THEN tutte le mutazioni riflesse."""

    @pytest.fixture
    def char_id(self, client):
        r = client.post("/api/db/characters", json={"name": "PatchFlow10", "kind": "npc"})
        assert r.status_code == 201
        return r.get_json()["id"]

    def test_patch_name_reflected(self, client, char_id):
        """WHEN PATCH name / THEN GET mostra nuovo nome."""
        client.patch(f"/api/db/characters/{char_id}", json={"name": "PatchFlow10-Renamed"})
        d = client.get(f"/api/db/characters/{char_id}").get_json()
        char = d.get("character") or d
        assert char["name"] == "PatchFlow10-Renamed"

    def test_patch_image_path_reflected(self, client, char_id):
        """WHEN PATCH image_path / THEN GET mostra il path."""
        client.patch(f"/api/db/characters/{char_id}", json={"image_path": "/static/avatars/test.png"})
        d = client.get(f"/api/db/characters/{char_id}").get_json()
        char = d.get("character") or d
        assert char.get("image_path") == "/static/avatars/test.png"

    def test_patch_kind_invalid_returns_400(self, client, char_id):
        """WHEN PATCH kind invalido / THEN 400 Bad Request."""
        r = client.patch(f"/api/db/characters/{char_id}", json={"kind": "villain"})
        assert r.status_code == 400

    def test_patch_nonexistent_returns_404(self, client):
        """WHEN PATCH personaggio inesistente / THEN 404."""
        r = client.patch("/api/db/characters/id-che-non-esiste", json={"kind": "npc"})
        assert r.status_code == 404


# ── FLOW-11: Messages recent — pannello ◇ Messages ───────────────────────────

class TestFlow11MessagesRecent:
    """GIVEN messaggi nel DB / WHEN GET /api/db/messages/recent / THEN lista con campi."""

    def test_recent_messages_returns_200(self, client):
        r = client.get("/api/db/messages/recent?limit=5")
        assert r.status_code == 200

    def test_recent_messages_has_messages_key(self, client):
        d = client.get("/api/db/messages/recent?limit=5").get_json()
        assert "messages" in d

    def test_recent_messages_is_list(self, client):
        d = client.get("/api/db/messages/recent?limit=5").get_json()
        assert isinstance(d["messages"], list)

    def test_recent_messages_limit_respected(self, client):
        d = client.get("/api/db/messages/recent?limit=3").get_json()
        assert len(d["messages"]) <= 3

    def test_recent_messages_have_required_fields(self, client):
        """Ogni messaggio ha id, author_name, content_original, scene_id."""
        d = client.get("/api/db/messages/recent?limit=5").get_json()
        for m in d["messages"]:
            assert "id" in m, f"id assente: {m}"
            assert "author_name" in m, f"author_name assente: {m}"
            assert "content_original" in m, f"content_original assente: {m}"

    def test_source_filter_discord(self, client):
        """Filtro source=discord ritorna messaggi Discord."""
        d = client.get("/api/db/messages/recent?source=discord&limit=3").get_json()
        for m in d["messages"]:
            assert m.get("source") == "discord"


# ── FLOW-12: LoreKB CRUD — /api/lore/entries ─────────────────────────────────

class TestFlow12LoreKbCrud:
    """GIVEN app avviata / WHEN CRUD /api/lore/entries / THEN lifecycle completo."""

    def test_categories_returns_list(self, client):
        d = client.get("/api/lore/categories").get_json()
        cats = d.get("categories", [])
        assert isinstance(cats, list) and len(cats) >= 1

    def test_post_entry_returns_201(self, client):
        r = client.post("/api/lore/entries", json={
            "title": "TestLore-Journey12", "body": "Corpo di test.", "category": "other"
        })
        assert r.status_code == 201
        assert "id" in r.get_json()

    def test_get_entry_after_post(self, client):
        r = client.post("/api/lore/entries", json={
            "title": "TestLore-Journey12-Get", "body": "Corpo get.", "category": "other"
        })
        eid = r.get_json()["id"]
        d = client.get(f"/api/lore/entries/{eid}").get_json()
        assert d.get("title") == "TestLore-Journey12-Get"

    def test_delete_entry_returns_200(self, client):
        r = client.post("/api/lore/entries", json={
            "title": "TestLore-Journey12-Del", "body": "Da eliminare.", "category": "other"
        })
        eid = r.get_json()["id"]
        r2 = client.delete(f"/api/lore/entries/{eid}")
        assert r2.status_code == 200

    def test_get_deleted_entry_returns_404(self, client):
        r = client.post("/api/lore/entries", json={
            "title": "TestLore-Journey12-404", "body": ".", "category": "other"
        })
        eid = r.get_json()["id"]
        client.delete(f"/api/lore/entries/{eid}")
        r2 = client.get(f"/api/lore/entries/{eid}")
        assert r2.status_code == 404


# ── FLOW-13: Arc creation lifecycle ──────────────────────────────────────────

class TestFlow13ArcCreate:
    """GIVEN app / WHEN POST /api/arc / THEN 201 + arco visibile in GET /api/arc."""

    ARC_ID = "arc_test_flow13"

    def test_create_arc_returns_201(self, client):
        r = client.post("/api/arc", json={
            "arc_id": self.ARC_ID, "title": "Flow13 TestArc", "chars": ["Arianna"]
        })
        assert r.status_code == 201
        d = r.get_json()
        assert d.get("arc_id") == self.ARC_ID

    def test_arc_visible_in_list(self, client):
        client.post("/api/arc", json={
            "arc_id": self.ARC_ID, "title": "Flow13 TestArc", "chars": []
        })
        r = client.get("/api/arc")
        arcs = r.get_json()
        assert any(a.get("arc_id") == self.ARC_ID for a in arcs)

    def test_get_single_arc(self, client):
        client.post("/api/arc", json={
            "arc_id": self.ARC_ID, "title": "Flow13 TestArc", "chars": []
        })
        r = client.get(f"/api/arc/{self.ARC_ID}")
        assert r.status_code == 200
        assert r.get_json().get("arc_id") == self.ARC_ID

    def test_delete_arc_not_implemented_returns_405(self, client):
        """DELETE /api/arc non implementato — sistema YAML non ha questo endpoint."""
        r = client.delete(f"/api/arc/{self.ARC_ID}")
        assert r.status_code == 405


# ── FLOW-14: Dashboard API endpoints ─────────────────────────────────────────

class TestFlow14DashboardApi:
    """GIVEN app / WHEN GET /api/dashboard/* / THEN 200 con struttura attesa."""

    def test_counts_returns_200(self, client):
        r = client.get("/api/dashboard/counts")
        assert r.status_code == 200

    def test_counts_has_chars_and_scenes(self, client):
        d = client.get("/api/dashboard/counts").get_json()
        assert "chars" in d
        assert "scenes" in d

    def test_activity_returns_200(self, client):
        r = client.get("/api/dashboard/activity")
        assert r.status_code == 200

    def test_activity_has_events_key(self, client):
        d = client.get("/api/dashboard/activity").get_json()
        assert "events" in d

    def test_snapshot_returns_200(self, client):
        r = client.get("/api/dashboard/snapshot")
        assert r.status_code == 200

    def test_health_endpoint_returns_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.get_json().get("status") == "ok"


# ── FLOW-15: Mascot state API ─────────────────────────────────────────────────

class TestFlow15MascotState:
    """GIVEN app / WHEN GET /api/mascot/state / THEN 200 con emotion + ws_url."""

    def test_mascot_state_returns_200(self, client):
        r = client.get("/api/mascot/state")
        assert r.status_code == 200

    def test_mascot_state_has_emotion(self, client):
        d = client.get("/api/mascot/state").get_json()
        assert "emotion" in d

    def test_mascot_emotion_map_returns_200(self, client):
        r = client.get("/api/mascot/emotion_map")
        assert r.status_code == 200

    def test_mascot_state_post_updates_emotion(self, client):
        """POST /api/mascot/state aggiorna emotion — PATCH non implementato (405)."""
        r = client.post("/api/mascot/state", json={"emotion": "happy", "intensity": 0.8})
        assert r.status_code in (200, 204)
        r2 = client.get("/api/mascot/state")
        assert r2.get_json().get("emotion") == "happy"


# ── FLOW-16: Char memory endpoints ───────────────────────────────────────────

class TestFlow16CharMemory:
    """GIVEN app / WHEN char memory API / THEN struttura response corretta."""

    def test_chars_memory_returns_200(self, client):
        """GET /api/chars/<name>/memory — snippets ChromaDB."""
        r = client.get("/api/chars/Arianna/memory")
        assert r.status_code == 200

    def test_chars_memory_has_snippets_key(self, client):
        d = client.get("/api/chars/Arianna/memory").get_json()
        assert "snippets" in d
        assert isinstance(d["snippets"], list)

    def test_char_facts_returns_200(self, client):
        """GET /api/char/<name>/facts — fatti strutturati dal char_memory module."""
        r = client.get("/api/char/Arianna/facts")
        assert r.status_code == 200

    def test_char_facts_has_facts_key(self, client):
        d = client.get("/api/char/Arianna/facts").get_json()
        assert "facts" in d

    def test_memory_append_returns_400_without_params(self, client):
        """POST /api/char/memory_append senza char+fact → 400."""
        r = client.post("/api/char/memory_append", json={})
        assert r.status_code == 400

    def test_memory_append_with_params_returns_200(self, client):
        """POST /api/char/memory_append con char+fact → 200."""
        r = client.post("/api/char/memory_append", json={
            "char": "Arianna", "fact": "Test fact journey16", "scope": "L1"
        })
        assert r.status_code == 200

    def test_recall_returns_400_without_params(self, client):
        """POST /api/char/recall senza char+query → 400."""
        r = client.post("/api/char/recall", json={})
        assert r.status_code == 400


# ── FLOW-17: Arc advanced routes ──────────────────────────────────────────────

class TestFlow17ArcAdvanced:
    """GIVEN arco esistente / WHEN arc sub-routes / THEN struttura corretta."""

    ARC_ID = "arc_flow17_test"

    @pytest.fixture(autouse=True)
    def setup_arc(self, client):
        client.post("/api/arc", json={
            "arc_id": self.ARC_ID, "title": "Flow17 Test Arc", "chars": ["Arianna"]
        })

    def test_arc_summary_returns_200(self, client):
        r = client.post(f"/api/arc/{self.ARC_ID}/summary")
        assert r.status_code == 200

    def test_arc_summary_has_summary_key(self, client):
        d = client.post(f"/api/arc/{self.ARC_ID}/summary").get_json()
        assert "summary" in d

    def test_arc_threads_returns_200(self, client):
        r = client.get(f"/api/arc/{self.ARC_ID}/threads")
        assert r.status_code == 200

    def test_arc_threads_has_threads_key(self, client):
        d = client.get(f"/api/arc/{self.ARC_ID}/threads").get_json()
        assert "threads" in d

    def test_arc_search_returns_results(self, client):
        r = client.post("/api/arc/search", json={"query": "Aurora combattimento magia"})
        assert r.status_code == 200
        assert "results" in r.get_json()

    def test_arc_append_without_md_path_returns_400(self, client):
        """arc/append richiede scene_md_path — senza → 400."""
        r = client.post(f"/api/arc/{self.ARC_ID}/append", json={
            "scene_id": "test", "title": "Test", "summary": "summary"
        })
        assert r.status_code == 400
        assert "error" in r.get_json()
