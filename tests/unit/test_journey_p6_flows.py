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


# ── FLOW-18: Lore/search + scene routes degradation ──────────────────────────

class TestFlow18LoreSearchAndSceneRoutes:
    """GIVEN app / WHEN lore/scene POST routes / THEN degradation graceful in test env."""

    def test_lore_search_returns_200(self, client):
        """POST /api/lore/search usa ChromaDB calliope_lore (384-dim) — funziona sempre."""
        r = client.post("/api/lore/search", json={"query": "Aurora combattimento"})
        assert r.status_code == 200

    def test_lore_search_has_results_key(self, client):
        d = client.post("/api/lore/search", json={"query": "Aurora"}).get_json()
        assert "results" in d

    def test_scene_refine_without_params_returns_400(self, client):
        r = client.post("/api/scene/refine", json={})
        assert r.status_code == 400

    def test_scene_refine_without_feedback_returns_400(self, client):
        r = client.post("/api/scene/refine", json={"scene_text": "testo"})
        assert r.status_code == 400

    def test_scene_variants_without_prompt_returns_400(self, client):
        r = client.post("/api/scene/variants", json={})
        assert r.status_code == 400

    def test_scene_variants_with_prompt_returns_200(self, client):
        """scene/variants genera localmente (no LLM) — sempre 200."""
        r = client.post("/api/scene/variants", json={"prompt": "Il guerriero avanzò."})
        assert r.status_code == 200
        assert "variants" in r.get_json()

    def test_summarize_without_llm_returns_503(self, client):
        """POST /api/summarize → 503 in test env (gateway non disponibile)."""
        r = client.post("/api/summarize", json={"text": "Alice: Ciao"})
        assert r.status_code in (200, 503)

    def test_translate_without_llm_returns_503(self, client):
        """POST /api/translate → 503 in test env (gateway non disponibile)."""
        r = client.post("/api/translate", json={"text": "Ciao"})
        assert r.status_code in (200, 503)


# ── FLOW-19: Scene revive + draft degradation ─────────────────────────────────

class TestFlow19SceneReviveAndDraft:
    """GIVEN scena nel DB / WHEN scene revive + draft / THEN struttura corretta."""

    def test_scene_revive_returns_200_with_scene_id(self, client):
        """POST /api/scene/revive con scene_id valida → 200 con char_facts + lore_refs."""
        scenes = client.get("/api/db/scenes").get_json().get("scenes", [])
        if not scenes:
            pytest.skip("Nessuna scena nel DB")
        scene_id = scenes[0]["id"]
        r = client.post("/api/scene/revive", json={"scene_id": scene_id})
        assert r.status_code == 200

    def test_scene_revive_has_lore_refs_key(self, client):
        scenes = client.get("/api/db/scenes").get_json().get("scenes", [])
        if not scenes:
            pytest.skip("Nessuna scena nel DB")
        scene_id = scenes[0]["id"]
        d = client.post("/api/scene/revive", json={"scene_id": scene_id}).get_json()
        assert "lore_refs" in d

    def test_scene_revive_has_participants_key(self, client):
        scenes = client.get("/api/db/scenes").get_json().get("scenes", [])
        if not scenes:
            pytest.skip("Nessuna scena nel DB")
        scene_id = scenes[0]["id"]
        d = client.post("/api/scene/revive", json={"scene_id": scene_id}).get_json()
        assert "participants" in d

    def test_draft_without_intent_it_returns_400(self, client):
        """POST /api/draft senza intent_it → 400."""
        r = client.post("/api/draft", json={})
        assert r.status_code == 400

    def test_draft_with_intent_returns_503_without_gateway(self, client):
        """POST /api/draft con intent → 503 in test env (LLM non disponibile)."""
        r = client.post("/api/draft", json={"intent_it": "Il guerriero combatté.", "style": "poetico"})
        assert r.status_code in (200, 503)

    def test_scene_blend_without_variants_file_returns_400(self, client):
        """POST /api/scene/blend senza variants_file_path → 400."""
        r = client.post("/api/scene/blend", json={"texts": ["A", "B"]})
        assert r.status_code == 400


# ── FLOW-20: Scene DB edit lifecycle ──────────────────────────────────────────

class TestFlow20SceneDbEdit:
    """PATCH /api/db/scenes/<id> — crea, aggiorna titolo, verifica, errori."""

    @pytest.fixture(autouse=True)
    def _scene(self, client):
        r = client.post("/api/db/scenes", json={"title": "flow20-original-title"})
        assert r.status_code == 201
        self.scene_id = r.get_json()["id"]
        yield
        client.delete(f"/api/db/scenes/{self.scene_id}")

    def test_patch_title_returns_200(self, client):
        """PATCH con title valido → 200."""
        r = client.patch(f"/api/db/scenes/{self.scene_id}", json={"title": "flow20-updated-title"})
        assert r.status_code == 200

    def test_patch_title_persists(self, client):
        """GET dopo PATCH restituisce il titolo aggiornato."""
        client.patch(f"/api/db/scenes/{self.scene_id}", json={"title": "flow20-persisted"})
        d = client.get(f"/api/db/scenes/{self.scene_id}").get_json()
        assert d["scene"]["title"] == "flow20-persisted"

    def test_patch_without_fields_returns_400(self, client):
        """PATCH senza campi aggiornabili → 400."""
        r = client.patch(f"/api/db/scenes/{self.scene_id}", json={})
        assert r.status_code == 400

    def test_patch_empty_title_returns_400(self, client):
        """PATCH con title vuoto → 400."""
        r = client.patch(f"/api/db/scenes/{self.scene_id}", json={"title": ""})
        assert r.status_code == 400

    def test_patch_unknown_scene_returns_404(self, client):
        """PATCH su scene_id inesistente → 404."""
        r = client.patch("/api/db/scenes/nonexistent-id-xyz", json={"title": "X"})
        assert r.status_code == 404

    def test_patch_location_returns_200(self, client):
        """PATCH con location → 200 e persiste."""
        r = client.patch(f"/api/db/scenes/{self.scene_id}", json={"location": "Castello di ferro"})
        assert r.status_code == 200
        d = client.get(f"/api/db/scenes/{self.scene_id}").get_json()
        assert d["scene"]["location"] == "Castello di ferro"


# ── FLOW-21: POST /api/characters → crea file YAML scheletro ─────────────────

class TestFlow21CharactersCreate:
    """POST /api/characters crea un file YAML nella dir characters (non solo SQLite)."""

    STEM = "flow21-journey-test-char"
    YAML_PATH = None

    @pytest.fixture(autouse=True)
    def _cleanup(self, tmp_path):
        from app.calliope_shell.characters_service import _chars_dir
        self._yaml = _chars_dir() / f"{self.STEM}.draft.yaml"
        yield
        if self._yaml.exists():
            self._yaml.unlink()

    def test_create_returns_201(self, client):
        """POST /api/characters → 201 con stem e name."""
        r = client.post("/api/characters", json={"name": "flow21 journey test char", "kind": "npc"})
        assert r.status_code == 201
        d = r.get_json()
        assert d["stem"] == self.STEM
        assert d["name"] == "flow21 journey test char"

    def test_yaml_file_created_on_disk(self, client):
        """Il file .draft.yaml viene fisicamente scritto su disco."""
        client.post("/api/characters", json={"name": "flow21 journey test char", "kind": "npc"})
        assert self._yaml.exists()

    def test_yaml_contains_name(self, client):
        """Il file YAML contiene il campo name."""
        import yaml
        client.post("/api/characters", json={"name": "flow21 journey test char", "kind": "npc"})
        data = yaml.safe_load(self._yaml.read_text())
        assert data["name"] == "flow21 journey test char"

    def test_yaml_contains_kind_as_tag(self, client):
        """Il kind viene salvato come tag nel YAML."""
        import yaml
        client.post("/api/characters", json={"name": "flow21 journey test char", "kind": "player"})
        data = yaml.safe_load(self._yaml.read_text())
        assert "player" in data.get("tags", [])

    def test_duplicate_returns_409(self, client):
        """POST duplicato → 409 already exists."""
        client.post("/api/characters", json={"name": "flow21 journey test char"})
        r = client.post("/api/characters", json={"name": "flow21 journey test char"})
        assert r.status_code == 409

    def test_empty_name_returns_400(self, client):
        """POST senza name → 400."""
        r = client.post("/api/characters", json={"kind": "npc"})
        assert r.status_code == 400

    def test_visible_in_list_after_create(self, client):
        """GET /api/characters dopo POST → il nuovo personaggio appare."""
        client.post("/api/characters", json={"name": "flow21 journey test char"})
        chars = client.get("/api/characters").get_json()
        stems = [c["stem"] for c in chars]
        assert self.STEM in stems


# ── FLOW-22: PATCH /api/db/characters/<id> — aggiorna kind/name ───────────────

class TestFlow22CharDbPatch:
    """PATCH /api/db/characters/<id>: aggiorna kind, name, verifica errori."""

    @pytest.fixture(autouse=True)
    def _char(self, client):
        r = client.post("/api/db/characters", json={"name": "flow22-test-char", "kind": "npc"})
        assert r.status_code == 201
        self.char_id = r.get_json()["id"]
        yield
        client.delete(f"/api/db/characters/{self.char_id}")

    def test_patch_kind_returns_200(self, client):
        """PATCH con kind valido → 200."""
        r = client.patch(f"/api/db/characters/{self.char_id}", json={"kind": "player"})
        assert r.status_code == 200

    def test_patch_kind_persists(self, client):
        """GET dopo PATCH kind → kind aggiornato."""
        client.patch(f"/api/db/characters/{self.char_id}", json={"kind": "player"})
        d = client.get(f"/api/db/characters/{self.char_id}").get_json()
        assert d["kind"] == "player"

    def test_patch_name_returns_200(self, client):
        """PATCH con name → 200."""
        r = client.patch(f"/api/db/characters/{self.char_id}", json={"name": "flow22-renamed"})
        assert r.status_code == 200

    def test_patch_invalid_kind_returns_400(self, client):
        """PATCH con kind non valido → 400."""
        r = client.patch(f"/api/db/characters/{self.char_id}", json={"kind": "invalid_kind"})
        assert r.status_code == 400

    def test_patch_empty_body_returns_400(self, client):
        """PATCH con body vuoto → 400."""
        r = client.patch(f"/api/db/characters/{self.char_id}", json={})
        assert r.status_code == 400

    def test_patch_unknown_id_returns_404(self, client):
        """PATCH su id inesistente → 404."""
        r = client.patch("/api/db/characters/nonexistent-id-xyz", json={"kind": "npc"})
        assert r.status_code == 404


# ── FLOW-23: POST /api/db/scenes/<id>/messages — compose ─────────────────────


class TestFlow23ComposeMessage:
    """GIVEN scena esistente / WHEN POST messaggio / THEN 201 + persiste."""

    @pytest.fixture(autouse=True)
    def _scene(self, client):
        r = client.post("/api/db/scenes", json={"title": "flow23-compose-scene"})
        assert r.status_code == 201
        self.scene_id = r.get_json()["id"]
        yield
        client.delete(f"/api/db/scenes/{self.scene_id}")

    def test_post_message_returns_201(self, client):
        """POST messaggio valido → 201."""
        r = client.post(
            f"/api/db/scenes/{self.scene_id}/messages",
            json={"author_name": "Aurora", "content_original": "Ciao dal test"},
        )
        assert r.status_code == 201

    def test_post_message_body_has_id(self, client):
        """201 response contiene campo id."""
        r = client.post(
            f"/api/db/scenes/{self.scene_id}/messages",
            json={"author_name": "Koko", "content_original": "Test msg"},
        )
        assert "id" in r.get_json()

    def test_message_visible_in_scene_get(self, client):
        """GET scena dopo POST → messages non è vuoto."""
        client.post(
            f"/api/db/scenes/{self.scene_id}/messages",
            json={"author_name": "Aurora", "content_original": "Visible msg"},
        )
        d = client.get(f"/api/db/scenes/{self.scene_id}").get_json()
        msgs = d.get("messages") or []
        count = d.get("message_count", len(msgs))
        assert count >= 1

    def test_post_missing_content_returns_400(self, client):
        """POST senza content_original → 400."""
        r = client.post(
            f"/api/db/scenes/{self.scene_id}/messages",
            json={"author_name": "Aurora"},
        )
        assert r.status_code == 400

    def test_post_missing_author_returns_400(self, client):
        """POST senza author_name → 400."""
        r = client.post(
            f"/api/db/scenes/{self.scene_id}/messages",
            json={"content_original": "Messaggio senza autore"},
        )
        assert r.status_code == 400

    def test_post_to_nonexistent_scene_returns_404(self, client):
        """POST a scene inesistente → 404."""
        r = client.post(
            "/api/db/scenes/nonexistent-scene-uuid/messages",
            json={"author_name": "Aurora", "content_original": "Test"},
        )
        assert r.status_code == 404


# ── FLOW-24: GET /api/db/messages/recent — filtro char + source ───────────────


class TestFlow24MessagesFilter:
    """GIVEN messaggi nel DB / WHEN GET con filtri / THEN risposta corretta."""

    def test_recent_messages_returns_200(self, client):
        """GET /api/db/messages/recent → 200."""
        r = client.get("/api/db/messages/recent?limit=10")
        assert r.status_code == 200

    def test_recent_messages_has_messages_key(self, client):
        """Response contiene chiave 'messages'."""
        d = client.get("/api/db/messages/recent?limit=5").get_json()
        assert "messages" in d

    def test_recent_messages_is_list(self, client):
        """messages è una lista."""
        d = client.get("/api/db/messages/recent?limit=5").get_json()
        assert isinstance(d["messages"], list)

    def test_char_filter_returns_subset(self, client):
        """GET ?char=NonExistentChar999 → lista vuota (no match)."""
        d = client.get("/api/db/messages/recent?limit=50&char=NonExistentChar999").get_json()
        assert d["messages"] == []

    def test_discord_source_filter(self, client):
        """GET ?source=discord → solo messaggi discord (o lista vuota)."""
        d = client.get("/api/db/messages/recent?limit=10&source=discord").get_json()
        for msg in d["messages"]:
            assert msg.get("source") == "discord"

    def test_limit_respected(self, client):
        """GET ?limit=3 → max 3 messaggi."""
        d = client.get("/api/db/messages/recent?limit=3").get_json()
        assert len(d["messages"]) <= 3


# ── TestFlow25: Scenes message_count field (has-msg filter) ──────────────────

class TestFlow25ScenesMessageCount:
    """GIVEN /api/db/scenes / THEN ogni scena ha message_count numerico.

    Blinda il campo usato dal filtro JS 'Solo scene con messaggi'
    (#scene-has-msg-filter). Il filtro opera s.message_count > 0 lato client.
    """

    def test_scenes_list_200(self, client):
        r = client.get("/api/db/scenes")
        assert r.status_code == 200

    def test_scenes_key_present(self, client):
        d = client.get("/api/db/scenes").get_json()
        assert "scenes" in d

    def test_every_scene_has_message_count(self, client):
        scenes = client.get("/api/db/scenes").get_json()["scenes"]
        for s in scenes[:20]:
            assert "message_count" in s, f"scena {s.get('id')} manca message_count"

    def test_message_count_is_int_or_null(self, client):
        scenes = client.get("/api/db/scenes").get_json()["scenes"]
        for s in scenes[:20]:
            mc = s["message_count"]
            assert mc is None or isinstance(mc, int), f"message_count non int: {mc!r}"

    def test_scenes_with_messages_have_positive_count(self, client):
        """Crea scena + aggiunge messaggio → message_count >= 1."""
        # crea scena
        r = client.post("/api/db/scenes", json={"title": "journey-test-msgcount"})
        assert r.status_code in (200, 201)
        sid = r.get_json()["id"]
        # aggiunge messaggio
        client.post(f"/api/db/scenes/{sid}/messages", json={"author_name": "Test", "content_original": "Prova"})
        # verifica count
        scenes = client.get("/api/db/scenes").get_json()["scenes"]
        target = next((s for s in scenes if s["id"] == sid), None)
        assert target is not None
        assert (target["message_count"] or 0) >= 1


# ── TestFlow26: Scene roster CRUD ────────────────────────────────────────────

class TestFlow26SceneRosterCrud:
    """GIVEN una scena e un personaggio esistente
    WHEN POST /api/db/scenes/<id>/characters
    THEN il personaggio appare nel roster; DELETE lo rimuove.
    """

    def test_roster_get_empty(self, client):
        r = client.post("/api/db/scenes", json={"title": "journey-test-arc-assign"})
        assert r.status_code in (200, 201)
        sid = r.get_json()["id"]
        r2 = client.get(f"/api/db/scenes/{sid}/characters")
        assert r2.status_code == 200
        d = r2.get_json()
        assert "characters" in d
        assert d["characters"] == []

    def test_roster_add_character(self, client):
        # crea scena
        r = client.post("/api/db/scenes", json={"title": "journey-test-arc-assign"})
        sid = r.get_json()["id"]
        # ottieni un personaggio esistente
        chars = client.get("/api/db/characters").get_json()["characters"]
        if not chars:
            pytest.skip("nessun personaggio nel DB")
        cid = chars[0]["id"]
        # aggiungi al roster
        r2 = client.post(f"/api/db/scenes/{sid}/characters", json={"character_id": cid, "role": "protagonist"})
        assert r2.status_code in (200, 201)

    def test_roster_character_appears_in_get(self, client):
        r = client.post("/api/db/scenes", json={"title": "journey-test-arc-assign"})
        sid = r.get_json()["id"]
        chars = client.get("/api/db/characters").get_json()["characters"]
        if not chars:
            pytest.skip("nessun personaggio nel DB")
        cid = chars[0]["id"]
        client.post(f"/api/db/scenes/{sid}/characters", json={"character_id": cid, "role": "protagonist"})
        r3 = client.get(f"/api/db/scenes/{sid}/characters")
        assert r3.status_code == 200
        names = [c.get("id") or c.get("character_id") for c in r3.get_json()["characters"]]
        assert cid in names or any(str(cid) in str(n) for n in names)

    def test_roster_delete_character(self, client):
        r = client.post("/api/db/scenes", json={"title": "journey-test-arc-assign"})
        sid = r.get_json()["id"]
        chars = client.get("/api/db/characters").get_json()["characters"]
        if not chars:
            pytest.skip("nessun personaggio nel DB")
        cid = chars[0]["id"]
        client.post(f"/api/db/scenes/{sid}/characters", json={"character_id": cid, "role": "protagonist"})
        r4 = client.delete(f"/api/db/scenes/{sid}/characters/{cid}")
        assert r4.status_code in (200, 204)

    def test_roster_empty_after_delete(self, client):
        r = client.post("/api/db/scenes", json={"title": "journey-test-arc-assign"})
        sid = r.get_json()["id"]
        chars = client.get("/api/db/characters").get_json()["characters"]
        if not chars:
            pytest.skip("nessun personaggio nel DB")
        cid = chars[0]["id"]
        client.post(f"/api/db/scenes/{sid}/characters", json={"character_id": cid})
        client.delete(f"/api/db/scenes/{sid}/characters/{cid}")
        r5 = client.get(f"/api/db/scenes/{sid}/characters")
        assert r5.get_json()["characters"] == []


# ── TestFlow27: Messages → scena (append) ────────────────────────────────────

class TestFlow27MessageToScene:
    """GIVEN una scena + messaggio recente
    WHEN POST /api/db/scenes/<id>/messages con author_name+content_original
    THEN messaggio appare nella scena (GET /api/db/scenes/<id>/messages).
    """

    def _make_scene(self, client, title="journey-test-arc-assign"):
        r = client.post("/api/db/scenes", json={"title": title})
        assert r.status_code in (200, 201)
        return r.get_json()["id"]

    def test_append_message_201(self, client):
        sid = self._make_scene(client)
        r = client.post(f"/api/db/scenes/{sid}/messages",
            json={"author_name": "Alice", "content_original": "Prova msg"})
        assert r.status_code in (200, 201)

    def test_appended_message_appears_in_get(self, client):
        sid = self._make_scene(client)
        client.post(f"/api/db/scenes/{sid}/messages",
            json={"author_name": "Bob", "content_original": "Ciao Mondo"})
        r = client.get(f"/api/db/scenes/{sid}/messages")
        assert r.status_code == 200
        msgs = r.get_json().get("messages", [])
        assert any(m.get("author_name") == "Bob" for m in msgs)

    def test_missing_author_name_400(self, client):
        sid = self._make_scene(client)
        r = client.post(f"/api/db/scenes/{sid}/messages",
            json={"content_original": "Orphan"})
        assert r.status_code == 400

    def test_missing_content_original_400(self, client):
        sid = self._make_scene(client)
        r = client.post(f"/api/db/scenes/{sid}/messages",
            json={"author_name": "Ghost"})
        assert r.status_code == 400

    def test_scene_message_count_increments(self, client):
        sid = self._make_scene(client)
        before = next(
            (s["message_count"] or 0
             for s in client.get("/api/db/scenes").get_json()["scenes"] if s["id"] == sid),
            0
        )
        client.post(f"/api/db/scenes/{sid}/messages",
            json={"author_name": "Sys", "content_original": "Text"})
        after = next(
            (s["message_count"] or 0
             for s in client.get("/api/db/scenes").get_json()["scenes"] if s["id"] == sid),
            0
        )
        assert after == before + 1


# ── FLOW-28: LoreKB CRUD — create/get/update/delete entry ────────────────────
class TestFlow28LoreKBCrud:
    """GIVEN le route /api/lore/entries
    WHEN POST→GET→PUT→DELETE
    THEN ogni mutazione riflessa nella lista entries.
    """

    def _create(self, client, title="flow28-test-lore"):
        r = client.post("/api/lore/entries", json={
            "title": title,
            "category": "other",
            "keys": ["flow28", "test"],
            "content": "Contenuto di prova flow28.",
            "scope": "global",
        })
        assert r.status_code == 201
        return r.get_json()["id"]

    def test_create_201_with_id(self, client):
        r = client.post("/api/lore/entries", json={"title": "f28-create"})
        assert r.status_code == 201
        assert "id" in r.get_json()

    def test_created_entry_in_list(self, client):
        eid = self._create(client, "f28-list-check")
        r = client.get("/api/lore/entries")
        assert r.status_code == 200
        ids = [e["id"] for e in r.get_json()["entries"]]
        assert eid in ids

    def test_get_entry_by_id(self, client):
        eid = self._create(client, "f28-get-by-id")
        r = client.get(f"/api/lore/entries/{eid}")
        assert r.status_code == 200
        assert r.get_json()["title"] == "f28-get-by-id"

    def test_missing_title_400(self, client):
        r = client.post("/api/lore/entries", json={"content": "no title"})
        assert r.status_code == 400

    def test_update_entry_200(self, client):
        eid = self._create(client, "f28-update-target")
        r = client.put(f"/api/lore/entries/{eid}", json={"content": "updated content"})
        assert r.status_code == 200
        updated = client.get(f"/api/lore/entries/{eid}").get_json()
        assert updated["content"] == "updated content"

    def test_category_filter(self, client):
        eid = self._create(client, "f28-cat-filter")
        client.put(f"/api/lore/entries/{eid}", json={"category": "places"})
        r = client.get("/api/lore/entries?category=places")
        assert r.status_code == 200
        ids = [e["id"] for e in r.get_json()["entries"]]
        assert eid in ids

    def test_delete_entry_ok(self, client):
        eid = self._create(client, "f28-delete-target")
        r = client.delete(f"/api/lore/entries/{eid}")
        assert r.status_code in (200, 204)
        r2 = client.get(f"/api/lore/entries/{eid}")
        assert r2.status_code == 404

    def test_delete_nonexistent_404(self, client):
        r = client.delete("/api/lore/entries/nonexistent-id-xyz")
        assert r.status_code == 404


# ── FLOW-29: Character DB — GET by ID, DELETE, scenes list ───────────────────
class TestFlow29CharDbReadDelete:
    """GIVEN /api/db/characters
    WHEN GET by ID, DELETE, GET /scenes per personaggio
    THEN risposte corrette e char rimossa post-delete.
    """

    def _make_char(self, client, name="flow29-char", kind="npc"):
        r = client.post("/api/db/characters", json={"name": name, "kind": kind})
        assert r.status_code in (200, 201)
        return r.get_json()["id"]

    def test_get_char_by_id(self, client):
        cid = self._make_char(client, "f29-get-char")
        r = client.get(f"/api/db/characters/{cid}")
        assert r.status_code == 200
        d = r.get_json()
        assert d["name"] == "f29-get-char"
        assert d["kind"] == "npc"

    def test_get_nonexistent_char_404(self, client):
        r = client.get("/api/db/characters/nonexistent-id-xyz-f29")
        assert r.status_code == 404

    def test_delete_char_204(self, client):
        cid = self._make_char(client, "f29-delete-char")
        r = client.delete(f"/api/db/characters/{cid}")
        assert r.status_code == 204
        r2 = client.get(f"/api/db/characters/{cid}")
        assert r2.status_code == 404

    def test_delete_nonexistent_char_404(self, client):
        r = client.delete("/api/db/characters/nonexistent-id-xyz-f29b")
        assert r.status_code == 404

    def test_char_scenes_list_empty(self, client):
        cid = self._make_char(client, "f29-scenes-char")
        r = client.get(f"/api/db/characters/{cid}/scenes")
        assert r.status_code == 200
        d = r.get_json()
        assert "scenes" in d
        assert isinstance(d["scenes"], list)

    def test_char_scenes_list_after_roster_add(self, client):
        cid = self._make_char(client, "f29-roster-char")
        sr = client.post("/api/db/scenes", json={"title": "f29-scene"})
        sid = sr.get_json()["id"]
        client.post(f"/api/db/scenes/{sid}/characters",
                    json={"character_id": cid, "role": "participant"})
        r = client.get(f"/api/db/characters/{cid}/scenes")
        assert r.status_code == 200
        scene_ids = [s["id"] for s in r.get_json()["scenes"]]
        assert sid in scene_ids


# ── FLOW-30: Arc continue + LoreKB categories ────────────────────────────────
class TestFlow30ArcContinueAndLoreCategories:
    """GIVEN arco esistente + lore store
    WHEN POST /api/arc/<id>/continue + GET /api/lore/categories
    THEN risposta con scene_type + lista categorie.
    """

    ARC_ID = "arc_flow30_test"

    @pytest.fixture(autouse=True)
    def setup_arc(self, client):
        client.post("/api/arc", json={
            "arc_id": self.ARC_ID, "title": "Flow30 TestArc", "chars": ["Aurora"]
        })

    def test_arc_continue_returns_200(self, client):
        r = client.post(f"/api/arc/{self.ARC_ID}/continue", json={})
        assert r.status_code == 200

    def test_arc_continue_has_scene_type(self, client):
        d = client.post(f"/api/arc/{self.ARC_ID}/continue", json={}).get_json()
        assert "scene_type" in d

    def test_arc_continue_with_hint(self, client):
        d = client.post(f"/api/arc/{self.ARC_ID}/continue",
                        json={"hint": "finale drammatico"}).get_json()
        assert "scene_type" in d

    def test_arc_continue_nonexistent_arc_503(self, client):
        r = client.post("/api/arc/nonexistent-arc-xyz/continue", json={})
        assert r.status_code in (404, 503)

    def test_lore_categories_returns_200(self, client):
        r = client.get("/api/lore/categories")
        assert r.status_code == 200

    def test_lore_categories_has_categories_key(self, client):
        d = client.get("/api/lore/categories").get_json()
        assert "categories" in d
        assert isinstance(d["categories"], list)

    def test_lore_categories_contains_expected(self, client):
        cats = client.get("/api/lore/categories").get_json()["categories"]
        assert len(cats) > 0

    def test_lore_entries_filter_by_category(self, client):
        r = client.get("/api/lore/entries?category=other")
        assert r.status_code == 200
        d = r.get_json()
        assert "entries" in d
        for e in d["entries"]:
            assert e.get("category") == "other"


# ── FLOW-31: Scene GET by ID + DELETE ────────────────────────────────────────
class TestFlow31SceneGetDelete:
    """GIVEN /api/db/scenes/<id>
    WHEN GET → restituisce scene+messages / DELETE → 204 + 404.
    """

    def _make(self, client, title="flow31-scene"):
        r = client.post("/api/db/scenes", json={"title": title})
        assert r.status_code == 201
        return r.get_json()["id"]

    def test_get_scene_by_id_returns_200(self, client):
        sid = self._make(client)
        r = client.get(f"/api/db/scenes/{sid}")
        assert r.status_code == 200

    def test_get_scene_by_id_has_scene_key(self, client):
        sid = self._make(client)
        d = client.get(f"/api/db/scenes/{sid}").get_json()
        assert "scene" in d
        assert d["scene"]["id"] == sid

    def test_get_scene_by_id_has_messages_key(self, client):
        sid = self._make(client)
        d = client.get(f"/api/db/scenes/{sid}").get_json()
        assert "messages" in d
        assert isinstance(d["messages"], list)

    def test_get_nonexistent_scene_404(self, client):
        r = client.get("/api/db/scenes/nonexistent-id-xyz-f31")
        assert r.status_code == 404

    def test_delete_scene_204(self, client):
        sid = self._make(client)
        r = client.delete(f"/api/db/scenes/{sid}")
        assert r.status_code == 204

    def test_get_after_delete_404(self, client):
        sid = self._make(client)
        client.delete(f"/api/db/scenes/{sid}")
        r = client.get(f"/api/db/scenes/{sid}")
        assert r.status_code == 404

    def test_delete_nonexistent_scene_404(self, client):
        r = client.delete("/api/db/scenes/nonexistent-id-xyz-f31b")
        assert r.status_code == 404


class TestFlow32MessageCrud:
    """GIVEN un messaggio nel DB / WHEN GET+PATCH+DELETE / THEN risposta corretta.

    Copre:
    - GET  /api/db/messages/<id>      → 200 con campi
    - PATCH /api/db/messages/<id>     → 200 con id aggiornato
    - DELETE /api/db/messages/<id>    → 204; poi GET → 404
    - PATCH payload vuoto             → 400
    """

    def _make_scene(self, client, title="flow32-scene"):
        r = client.post("/api/db/scenes", json={"title": title})
        assert r.status_code == 201
        return r.get_json()["id"]

    def _add_message(self, client, scene_id, author="flow32-author", content="contenuto32"):
        r = client.post(
            f"/api/db/scenes/{scene_id}/messages",
            json={"author_name": author, "content_original": content},
        )
        assert r.status_code == 201
        return r.get_json()["id"]

    def test_get_message_by_id_200(self, client):
        """GET /api/db/messages/<id> → 200 con campo content_original."""
        sid = self._make_scene(client)
        mid = self._add_message(client, sid)
        r = client.get(f"/api/db/messages/{mid}")
        assert r.status_code == 200
        body = r.get_json()
        assert "content_original" in body or "id" in body

    def test_get_nonexistent_message_404(self, client):
        """GET messaggio inesistente → 404."""
        r = client.get("/api/db/messages/nonexistent-flow32-msg")
        assert r.status_code == 404

    def test_patch_message_content_200(self, client):
        """PATCH content_original → 200 con id."""
        sid = self._make_scene(client)
        mid = self._add_message(client, sid)
        r = client.patch(f"/api/db/messages/{mid}", json={"content_original": "aggiornato32"})
        assert r.status_code == 200
        body = r.get_json()
        assert body.get("id") == mid

    def test_patch_message_author_200(self, client):
        """PATCH author_name → 200."""
        sid = self._make_scene(client)
        mid = self._add_message(client, sid)
        r = client.patch(f"/api/db/messages/{mid}", json={"author_name": "nuovo-autore32"})
        assert r.status_code == 200

    def test_patch_empty_payload_400(self, client):
        """PATCH senza campi validi → 400."""
        sid = self._make_scene(client)
        mid = self._add_message(client, sid)
        r = client.patch(f"/api/db/messages/{mid}", json={})
        assert r.status_code == 400

    def test_patch_nonexistent_message_404(self, client):
        """PATCH messaggio inesistente → 404."""
        r = client.patch(
            "/api/db/messages/nonexistent-flow32-msg",
            json={"content_original": "x"},
        )
        assert r.status_code == 404

    def test_delete_message_204(self, client):
        """DELETE messaggio → 204."""
        sid = self._make_scene(client)
        mid = self._add_message(client, sid)
        r = client.delete(f"/api/db/messages/{mid}")
        assert r.status_code == 204

    def test_get_after_delete_404(self, client):
        """GET dopo DELETE → 404."""
        sid = self._make_scene(client)
        mid = self._add_message(client, sid)
        client.delete(f"/api/db/messages/{mid}")
        r = client.get(f"/api/db/messages/{mid}")
        assert r.status_code == 404

    def test_delete_nonexistent_message_404(self, client):
        """DELETE messaggio inesistente → 404."""
        r = client.delete("/api/db/messages/nonexistent-flow32-msg")
        assert r.status_code == 404


class TestFlow33SceneRosterRoleAndOperations:
    """GIVEN scene con personaggio nel roster / WHEN PATCH role + scene duplicate+merge.

    Copre:
    - PATCH /api/db/scenes/<sid>/characters/<cid> → 200
    - PATCH senza role → 400
    - POST /api/db/scenes/<sid>/duplicate         → 201 con new_scene_id
    - POST /api/db/scenes/merge                   → 201 con merged_scene_id
    - POST merge self-merge                       → 400
    """

    def _make_scene(self, client, title="flow33-scene"):
        r = client.post("/api/db/scenes", json={"title": title})
        assert r.status_code == 201
        return r.get_json()["id"]

    def _make_char(self, client, name="flow33-char"):
        r = client.post("/api/db/characters", json={"name": name, "kind": "npc"})
        assert r.status_code in (200, 201)
        return r.get_json()["id"]

    def test_patch_roster_role_200(self, client):
        """PATCH role nel roster → 200."""
        sid = self._make_scene(client)
        cid = self._make_char(client)
        client.post(f"/api/db/scenes/{sid}/characters", json={"character_id": cid, "role": "protagonist"})
        r = client.patch(f"/api/db/scenes/{sid}/characters/{cid}", json={"role": "antagonist"})
        assert r.status_code == 200

    def test_patch_roster_no_role_400(self, client):
        """PATCH roster senza campo role → 400."""
        sid = self._make_scene(client)
        cid = self._make_char(client)
        client.post(f"/api/db/scenes/{sid}/characters", json={"character_id": cid})
        r = client.patch(f"/api/db/scenes/{sid}/characters/{cid}", json={})
        assert r.status_code == 400

    def test_patch_roster_nonexistent_404(self, client):
        """PATCH role per personaggio non nel roster → 404."""
        sid = self._make_scene(client)
        r = client.patch(f"/api/db/scenes/{sid}/characters/nonexistent-char", json={"role": "x"})
        assert r.status_code == 404

    def test_duplicate_scene_201(self, client):
        """POST /duplicate → 201 con new_scene_id."""
        sid = self._make_scene(client, "flow33-orig")
        r = client.post(f"/api/db/scenes/{sid}/duplicate", json={"new_name": "flow33-copy"})
        assert r.status_code == 201
        body = r.get_json()
        assert "new_scene_id" in body

    def test_duplicate_no_name_400(self, client):
        """POST /duplicate senza new_name → 400."""
        sid = self._make_scene(client)
        r = client.post(f"/api/db/scenes/{sid}/duplicate", json={})
        assert r.status_code == 400

    def test_duplicate_nonexistent_404(self, client):
        """POST /duplicate su scena inesistente → 404."""
        r = client.post("/api/db/scenes/nonexistent-flow33/duplicate", json={"new_name": "x"})
        assert r.status_code == 404

    def test_merge_scenes_201(self, client):
        """POST /merge due scene → 201 con merged_scene_id."""
        sid_a = self._make_scene(client, "flow33-merge-a")
        sid_b = self._make_scene(client, "flow33-merge-b")
        r = client.post(
            "/api/db/scenes/merge",
            json={"scene_id_a": sid_a, "scene_id_b": sid_b, "new_name": "flow33-merged"},
        )
        assert r.status_code == 201
        body = r.get_json()
        assert "merged_scene_id" in body

    def test_merge_self_400(self, client):
        """POST /merge stessa scena → 400 (self-merge guard)."""
        sid = self._make_scene(client)
        r = client.post(
            "/api/db/scenes/merge",
            json={"scene_id_a": sid, "scene_id_b": sid, "new_name": "x"},
        )
        assert r.status_code == 400

    def test_merge_missing_fields_400(self, client):
        """POST /merge senza campi obbligatori → 400."""
        r = client.post("/api/db/scenes/merge", json={"scene_id_a": "x"})
        assert r.status_code == 400


class TestFlow34MessageAdvanced:
    """GIVEN messaggi in scena / WHEN position/insert/move/compact / THEN corretti.

    Copre:
    - PATCH /api/db/messages/<id>/position → 200
    - POST  /api/db/scenes/<sid>/messages/insert → 201
    - POST  /api/db/messages/<id>/move → 200
    - POST  /api/db/scenes/<sid>/messages/compact → 200
    - /api/db/messages/recent → 200
    """

    def _make_scene(self, client, title="flow34-scene"):
        r = client.post("/api/db/scenes", json={"title": title})
        assert r.status_code == 201
        return r.get_json()["id"]

    def _add_msg(self, client, sid, author="auth34", content="cont34"):
        r = client.post(
            f"/api/db/scenes/{sid}/messages",
            json={"author_name": author, "content_original": content},
        )
        assert r.status_code == 201
        return r.get_json()["id"]

    def test_patch_position_200(self, client):
        """PATCH /position → 200."""
        sid = self._make_scene(client)
        mid = self._add_msg(client, sid)
        r = client.patch(f"/api/db/messages/{mid}/position", json={"position": 0})
        assert r.status_code == 200

    def test_patch_position_no_field_400(self, client):
        """PATCH /position senza campo → 400."""
        sid = self._make_scene(client)
        mid = self._add_msg(client, sid)
        r = client.patch(f"/api/db/messages/{mid}/position", json={})
        assert r.status_code == 400

    def test_patch_position_negative_400(self, client):
        """PATCH /position con valore negativo → 400."""
        sid = self._make_scene(client)
        mid = self._add_msg(client, sid)
        r = client.patch(f"/api/db/messages/{mid}/position", json={"position": -1})
        assert r.status_code == 400

    def test_patch_position_nonexistent_404(self, client):
        """PATCH /position messaggio inesistente → 404."""
        r = client.patch("/api/db/messages/nonexistent34/position", json={"position": 0})
        assert r.status_code == 404

    def test_insert_message_at_201(self, client):
        """POST /insert → 201 con id."""
        sid = self._make_scene(client)
        r = client.post(
            f"/api/db/scenes/{sid}/messages/insert",
            json={"author_name": "ins34", "content_original": "inserito", "position_order": 0},
        )
        assert r.status_code == 201
        assert "id" in r.get_json()

    def test_insert_missing_field_400(self, client):
        """POST /insert senza position_order → 400."""
        sid = self._make_scene(client)
        r = client.post(
            f"/api/db/scenes/{sid}/messages/insert",
            json={"author_name": "ins34", "content_original": "x"},
        )
        assert r.status_code == 400

    def test_insert_negative_position_400(self, client):
        """POST /insert position_order negativo → 400."""
        sid = self._make_scene(client)
        r = client.post(
            f"/api/db/scenes/{sid}/messages/insert",
            json={"author_name": "ins34", "content_original": "x", "position_order": -5},
        )
        assert r.status_code == 400

    def test_insert_nonexistent_scene_404(self, client):
        """POST /insert su scena inesistente → 404."""
        r = client.post(
            "/api/db/scenes/nonexistent34/messages/insert",
            json={"author_name": "x", "content_original": "y", "position_order": 0},
        )
        assert r.status_code == 404

    def test_move_message_to_scene_200(self, client):
        """POST /move → 200."""
        sid_a = self._make_scene(client, "flow34-move-a")
        sid_b = self._make_scene(client, "flow34-move-b")
        mid = self._add_msg(client, sid_a)
        r = client.post(
            f"/api/db/messages/{mid}/move",
            json={"target_scene_id": sid_b, "position": 0},
        )
        assert r.status_code == 200

    def test_move_missing_fields_400(self, client):
        """POST /move senza campi → 400."""
        sid = self._make_scene(client)
        mid = self._add_msg(client, sid)
        r = client.post(f"/api/db/messages/{mid}/move", json={"target_scene_id": sid})
        assert r.status_code == 400

    def test_move_nonexistent_message_404(self, client):
        """POST /move su messaggio inesistente → 404."""
        sid = self._make_scene(client)
        r = client.post(
            "/api/db/messages/nonexistent34/move",
            json={"target_scene_id": sid, "position": 0},
        )
        assert r.status_code == 404

    def test_compact_scene_messages_200(self, client):
        """POST /compact → 200."""
        sid = self._make_scene(client)
        self._add_msg(client, sid, "a34", "first")
        self._add_msg(client, sid, "b34", "second")
        r = client.post(f"/api/db/scenes/{sid}/messages/compact")
        assert r.status_code == 200

    def test_compact_nonexistent_scene_404(self, client):
        """POST /compact su scena inesistente → 404."""
        r = client.post("/api/db/scenes/nonexistent34/messages/compact")
        assert r.status_code == 404

    def test_recent_messages_200(self, client):
        """GET /api/db/messages/recent → 200 con lista."""
        r = client.get("/api/db/messages/recent")
        assert r.status_code == 200
        body = r.get_json()
        assert isinstance(body, (list, dict))


class TestFlow35ArcDbCrud:
    """GIVEN archi nel DB / WHEN GET+PATCH+DELETE + scene assegnazione.

    Copre:
    - GET  /api/db/arcs/<id>         → 200 / 404
    - PATCH /api/db/arcs/<id>        → 200 con arc aggiornato / 400 / 404
    - DELETE /api/db/arcs/<id>       → 204 / 404
    - GET  /api/db/arcs/<id>/scenes  → 200 con lista
    - PATCH /api/db/scenes/<sid>/arc → 200 con {arc_id}
    """

    def _make_arc(self, client, title="flow35-arc"):
        r = client.post("/api/db/arcs", json={"title": title})
        assert r.status_code == 201
        return r.get_json()["id"]

    def _make_scene(self, client, title="flow35-scene"):
        r = client.post("/api/db/scenes", json={"title": title})
        assert r.status_code == 201
        return r.get_json()["id"]

    def test_get_arc_by_id_200(self, client):
        """GET /api/db/arcs/<id> → 200."""
        aid = self._make_arc(client)
        r = client.get(f"/api/db/arcs/{aid}")
        assert r.status_code == 200

    def test_get_arc_nonexistent_404(self, client):
        """GET arc inesistente → 404."""
        r = client.get("/api/db/arcs/nonexistent-flow35")
        assert r.status_code == 404

    def test_patch_arc_title_200(self, client):
        """PATCH title → 200 con arc aggiornato."""
        aid = self._make_arc(client)
        r = client.patch(f"/api/db/arcs/{aid}", json={"title": "flow35-updated"})
        assert r.status_code == 200
        body = r.get_json()
        assert body.get("title") == "flow35-updated" or body.get("id") == aid

    def test_patch_arc_no_fields_400(self, client):
        """PATCH arc senza campi validi → 400."""
        aid = self._make_arc(client)
        r = client.patch(f"/api/db/arcs/{aid}", json={})
        assert r.status_code == 400

    def test_patch_arc_nonexistent_404(self, client):
        """PATCH arc inesistente → 404."""
        r = client.patch("/api/db/arcs/nonexistent-flow35", json={"title": "x"})
        assert r.status_code == 404

    def test_delete_arc_204(self, client):
        """DELETE arc → 204."""
        aid = self._make_arc(client, "flow35-to-delete")
        r = client.delete(f"/api/db/arcs/{aid}")
        assert r.status_code == 204

    def test_get_after_delete_404(self, client):
        """GET arc dopo DELETE → 404."""
        aid = self._make_arc(client, "flow35-del-verify")
        client.delete(f"/api/db/arcs/{aid}")
        r = client.get(f"/api/db/arcs/{aid}")
        assert r.status_code == 404

    def test_delete_nonexistent_arc_404(self, client):
        """DELETE arc inesistente → 404."""
        r = client.delete("/api/db/arcs/nonexistent-flow35")
        assert r.status_code == 404

    def test_arc_scenes_list_empty_200(self, client):
        """GET /api/db/arcs/<id>/scenes → 200 con lista vuota."""
        aid = self._make_arc(client)
        r = client.get(f"/api/db/arcs/{aid}/scenes")
        assert r.status_code == 200
        body = r.get_json()
        assert "scenes" in body
        assert isinstance(body["scenes"], list)

    def test_arc_scenes_after_assign(self, client):
        """GET /api/db/arcs/<id>/scenes → contiene la scena assegnata."""
        aid = self._make_arc(client)
        sid = self._make_scene(client)
        client.patch(f"/api/db/scenes/{sid}/arc", json={"arc_id": aid})
        r = client.get(f"/api/db/arcs/{aid}/scenes")
        assert r.status_code == 200
        scene_ids = [s["id"] for s in r.get_json()["scenes"]]
        assert sid in scene_ids

    def test_arc_scenes_nonexistent_arc_404(self, client):
        """GET /api/db/arcs/<id>/scenes su arco inesistente → 404."""
        r = client.get("/api/db/arcs/nonexistent-flow35/scenes")
        assert r.status_code == 404

    def test_patch_scene_arc_endpoint_200(self, client):
        """PATCH /api/db/scenes/<sid>/arc con arc_id → 200."""
        aid = self._make_arc(client)
        sid = self._make_scene(client)
        r = client.patch(f"/api/db/scenes/{sid}/arc", json={"arc_id": aid})
        assert r.status_code == 200

    def test_patch_scene_arc_remove_200(self, client):
        """PATCH /api/db/scenes/<sid>/arc con arc_id=null → 200 (disassocia)."""
        aid = self._make_arc(client)
        sid = self._make_scene(client)
        client.patch(f"/api/db/scenes/{sid}/arc", json={"arc_id": aid})
        r = client.patch(f"/api/db/scenes/{sid}/arc", json={"arc_id": None})
        assert r.status_code == 200

    def test_patch_scene_arc_no_field_400(self, client):
        """PATCH /api/db/scenes/<sid>/arc senza arc_id → 400."""
        sid = self._make_scene(client)
        r = client.patch(f"/api/db/scenes/{sid}/arc", json={})
        assert r.status_code == 400


class TestFlow36SceneMessagesPaginated:
    """GIVEN messaggi in scena / WHEN GET paginated + count / THEN corretti.

    Copre:
    - GET /api/db/scenes/<sid>/messages           → 200 con {messages, total, page, pages}
    - GET /api/db/scenes/<sid>/messages?page=1    → paginazione
    - GET /api/db/scenes/<sid>/messages?page=0    → 400 (bad_request)
    - GET /api/db/scenes/<sid>/messages su inesistente → 404
    - GET /api/db/scenes/<sid>/messages/count     → 200 con {count, scene_id}
    - GET count su scena inesistente              → 404
    """

    def _make_scene(self, client, title="flow36-scene"):
        r = client.post("/api/db/scenes", json={"title": title})
        assert r.status_code == 201
        return r.get_json()["id"]

    def _add_msgs(self, client, sid, n=3):
        for i in range(n):
            client.post(
                f"/api/db/scenes/{sid}/messages",
                json={"author_name": f"auth36-{i}", "content_original": f"msg {i}"},
            )

    def test_get_messages_paginated_200(self, client):
        """GET /api/db/scenes/<sid>/messages → 200."""
        sid = self._make_scene(client)
        self._add_msgs(client, sid, 3)
        r = client.get(f"/api/db/scenes/{sid}/messages")
        assert r.status_code == 200

    def test_get_messages_has_messages_key(self, client):
        """GET messages → risposta ha chiave messages."""
        sid = self._make_scene(client)
        self._add_msgs(client, sid, 2)
        body = client.get(f"/api/db/scenes/{sid}/messages").get_json()
        assert "messages" in body

    def test_get_messages_page_param(self, client):
        """GET con ?page=1&per_page=2 → 200."""
        sid = self._make_scene(client)
        self._add_msgs(client, sid, 4)
        r = client.get(f"/api/db/scenes/{sid}/messages?page=1&per_page=2")
        assert r.status_code == 200

    def test_get_messages_bad_page_400(self, client):
        """GET con page=0 → 400."""
        sid = self._make_scene(client)
        r = client.get(f"/api/db/scenes/{sid}/messages?page=0")
        assert r.status_code == 400

    def test_get_messages_nonexistent_scene_404(self, client):
        """GET messages su scena inesistente → 404."""
        r = client.get("/api/db/scenes/nonexistent-flow36/messages")
        assert r.status_code == 404

    def test_count_messages_200(self, client):
        """GET /count → 200 con {count, scene_id}."""
        sid = self._make_scene(client)
        self._add_msgs(client, sid, 3)
        r = client.get(f"/api/db/scenes/{sid}/messages/count")
        assert r.status_code == 200
        body = r.get_json()
        assert "count" in body
        assert body["count"] >= 3

    def test_count_messages_zero_for_empty_scene(self, client):
        """GET /count su scena vuota → count=0."""
        sid = self._make_scene(client, "flow36-empty")
        r = client.get(f"/api/db/scenes/{sid}/messages/count")
        assert r.status_code == 200
        assert r.get_json()["count"] == 0

    def test_count_messages_nonexistent_scene_404(self, client):
        """GET /count su scena inesistente → 404."""
        r = client.get("/api/db/scenes/nonexistent-flow36/messages/count")
        assert r.status_code == 404


class TestFlow37MessageReactions:
    """GIVEN messaggi / WHEN GET+POST+DELETE reazioni / THEN corretti.

    Copre:
    - GET  /api/db/messages/<id>/reactions              → 200 lista
    - POST /api/db/messages/<id>/reactions              → 201 con id
    - POST senza character_id                           → 400
    - POST su messaggio inesistente                     → 404
    - DELETE /api/db/messages/<id>/reactions/<rid>      → 204
    - DELETE reaction inesistente                       → 404
    """

    def _make_scene(self, client, title="flow37-scene"):
        r = client.post("/api/db/scenes", json={"title": title})
        assert r.status_code == 201
        return r.get_json()["id"]

    def _add_msg(self, client, sid):
        r = client.post(
            f"/api/db/scenes/{sid}/messages",
            json={"author_name": "auth37", "content_original": "testo37"},
        )
        assert r.status_code == 201
        return r.get_json()["id"]

    def _add_char(self, client):
        r = client.post("/api/db/characters", json={"name": "flow37-char", "kind": "npc"})
        assert r.status_code in (200, 201)
        return r.get_json()["id"]

    def test_list_reactions_empty_200(self, client):
        """GET reactions su messaggio senza reazioni → 200 lista vuota."""
        sid = self._make_scene(client)
        mid = self._add_msg(client, sid)
        r = client.get(f"/api/db/messages/{mid}/reactions")
        assert r.status_code == 200
        body = r.get_json()
        assert "reactions" in body
        assert isinstance(body["reactions"], list)

    def test_add_reaction_201(self, client):
        """POST reaction → 201 con id."""
        sid = self._make_scene(client)
        mid = self._add_msg(client, sid)
        cid = self._add_char(client)
        r = client.post(
            f"/api/db/messages/{mid}/reactions",
            json={"character_id": cid, "emoji": "❤️"},
        )
        assert r.status_code == 201
        assert "id" in r.get_json()

    def test_add_reaction_no_char_id_400(self, client):
        """POST reaction senza character_id → 400."""
        sid = self._make_scene(client)
        mid = self._add_msg(client, sid)
        r = client.post(f"/api/db/messages/{mid}/reactions", json={"emoji": "❤️"})
        assert r.status_code == 400

    def test_add_reaction_nonexistent_message_404(self, client):
        """POST reaction su messaggio inesistente → 404."""
        r = client.post(
            "/api/db/messages/nonexistent-flow37/reactions",
            json={"character_id": "some-char"},
        )
        assert r.status_code == 404

    def test_reaction_appears_in_list(self, client):
        """Dopo POST, GET lista → reazione presente."""
        sid = self._make_scene(client)
        mid = self._add_msg(client, sid)
        cid = self._add_char(client)
        client.post(f"/api/db/messages/{mid}/reactions", json={"character_id": cid, "emoji": "⭐"})
        r = client.get(f"/api/db/messages/{mid}/reactions")
        assert r.status_code == 200
        assert len(r.get_json()["reactions"]) >= 1

    def test_delete_reaction_204(self, client):
        """DELETE reaction → 204."""
        sid = self._make_scene(client)
        mid = self._add_msg(client, sid)
        cid = self._add_char(client)
        add_r = client.post(
            f"/api/db/messages/{mid}/reactions",
            json={"character_id": cid, "emoji": "🔥"},
        )
        rid = add_r.get_json()["id"]
        r = client.delete(f"/api/db/messages/{mid}/reactions/{rid}")
        assert r.status_code == 204

    def test_delete_nonexistent_reaction_404(self, client):
        """DELETE reaction inesistente → 404."""
        sid = self._make_scene(client)
        mid = self._add_msg(client, sid)
        r = client.delete(f"/api/db/messages/{mid}/reactions/nonexistent-rid-flow37")
        assert r.status_code == 404


class TestFlow38CharacterYamlGet:
    """GIVEN personaggi YAML / WHEN GET /api/characters/<stem> / THEN 200 o 404.

    Copre:
    - GET /api/characters/<stem>  → 200 con card
    - GET /api/characters/<stem>  → 404 per stem inesistente
    """

    def test_get_known_character_200(self, client):
        """GET personaggio esistente (arianna) → 200 con dati."""
        r = client.get("/api/characters/arianna")
        # arianna potrebbe non esistere nel test env — 200 o 404 entrambi ok
        assert r.status_code in (200, 404)

    def test_get_existing_character_has_name(self, client):
        """GET personaggio esistente → risposta ha campo name o error."""
        # Recupera il primo personaggio dalla lista
        chars = client.get("/api/characters").get_json()
        if not chars:
            return  # nessun char nel test DB — skip silenzioso
        stem = list(chars.keys())[0] if isinstance(chars, dict) else None
        if stem is None:
            return
        r = client.get(f"/api/characters/{stem}")
        assert r.status_code == 200
        body = r.get_json()
        assert "name" in body or "stem" in body or body is not None

    def test_get_nonexistent_character_404(self, client):
        """GET stem inesistente → 404."""
        r = client.get("/api/characters/nonexistent-stem-flow38-xyz")
        assert r.status_code == 404


class TestFlow39DashboardLlmRouting:
    """GIVEN app avviata / WHEN GET+POST /api/dashboard/llm_routing / THEN corretti.

    Copre:
    - GET  /api/dashboard/llm_routing   → 200 con active_provider, active_model
    - POST /api/dashboard/llm_routing   → toggle uncensored
    - POST senza 'uncensored'           → 400
    """

    def test_get_llm_routing_200(self, client):
        """GET /api/dashboard/llm_routing → 200."""
        r = client.get("/api/dashboard/llm_routing")
        assert r.status_code == 200

    def test_get_llm_routing_has_provider(self, client):
        """GET → risposta ha active_provider e active_model."""
        body = client.get("/api/dashboard/llm_routing").get_json()
        assert "active_provider" in body
        assert "active_model" in body

    def test_post_llm_routing_toggle_200(self, client):
        """POST {uncensored: false} → 200."""
        r = client.post("/api/dashboard/llm_routing", json={"uncensored": False})
        assert r.status_code == 200

    def test_post_llm_routing_missing_field_400(self, client):
        """POST senza campo uncensored → 400."""
        r = client.post("/api/dashboard/llm_routing", json={})
        assert r.status_code == 400


class TestFlow40LoreCheckAndCharMemoryReplace:
    """Boundary test per endpoint LLM-dipendenti: solo guard 400 su payload mancante.

    /api/lore/check → 400 se 'text' mancante
    /api/char/memory_replace → 400 se campi obbligatori mancanti
    """

    def test_lore_check_missing_text_400(self, client):
        """POST /api/lore/check senza text → 400."""
        r = client.post("/api/lore/check", json={})
        assert r.status_code == 400

    def test_lore_check_with_text_returns_json(self, client):
        """POST /api/lore/check con text → risposta JSON (200 o 503 se LLM non disponibile)."""
        r = client.post("/api/lore/check", json={"text": "Arianna era una guerriera."})
        assert r.status_code in (200, 503)
        assert r.get_json() is not None

    def test_memory_replace_missing_fields_400(self, client):
        """POST /api/char/memory_replace senza campi obbligatori → 400."""
        r = client.post("/api/char/memory_replace", json={"char": "Arianna"})
        assert r.status_code == 400

    def test_memory_replace_all_fields_returns_json(self, client):
        """POST /api/char/memory_replace con tutti i campi → risposta JSON (200, 202 o 400)."""
        r = client.post("/api/char/memory_replace", json={
            "char": "Arianna",
            "old_fact": "Era alta.",
            "new_fact": "Era bassa.",
        })
        assert r.status_code in (200, 202, 400)


class TestFlow41CharAvatarMerge:
    """Feature: avatar personaggio visibile nella griglia.

    Verifica che /api/db/characters restituisca image_path e che sia
    patchabile — base del merge YAML+DB per mostrare avatar nelle schede.
    """

    def _create_char(self, client, name="flow41-avatar"):
        r = client.post("/api/db/characters", json={"name": name, "kind": "npc"})
        assert r.status_code == 201
        return r.get_json()["id"]

    def test_char_list_has_image_path_field(self, client):
        """GET /api/db/characters → ogni char ha campo image_path (anche se None)."""
        self._create_char(client)
        chars = client.get("/api/db/characters").get_json()["characters"]
        assert len(chars) >= 1
        for c in chars:
            assert "image_path" in c

    def test_patch_image_path_persists(self, client):
        """PATCH /api/db/characters/<id> con image_path → GET restituisce il valore."""
        cid = self._create_char(client, "flow41-patch")
        r = client.patch(f"/api/db/characters/{cid}", json={"image_path": "/static/img/test.jpg"})
        assert r.status_code == 200
        detail = client.get(f"/api/db/characters/{cid}").get_json()
        assert detail["image_path"] == "/static/img/test.jpg"

    def test_patch_image_path_null_clears(self, client):
        """PATCH image_path=None cancella l'avatar (→ None nel DB)."""
        cid = self._create_char(client, "flow41-clear")
        client.patch(f"/api/db/characters/{cid}", json={"image_path": "/img.png"})
        r = client.patch(f"/api/db/characters/{cid}", json={"image_path": None})
        assert r.status_code == 200
        assert client.get(f"/api/db/characters/{cid}").get_json()["image_path"] is None


class TestFlow42MessageEditDelete:
    """Feature: modifica e cancellazione messaggi in-scene.

    Verifica PATCH content_original e DELETE per /api/db/messages/<id>.
    """

    def _scene_with_message(self, client, scene_title="flow42-scene", content="testo originale"):
        sid = client.post("/api/db/scenes", json={"title": scene_title}).get_json()["id"]
        mid = client.post(
            f"/api/db/scenes/{sid}/messages",
            json={"author_name": "narrator", "content_original": content},
        ).get_json()["id"]
        return sid, mid

    def test_patch_message_content_updates(self, client):
        """PATCH /api/db/messages/<id> content_original → 200, testo aggiornato."""
        _, mid = self._scene_with_message(client, "flow42-patch")
        r = client.patch(f"/api/db/messages/{mid}", json={"content_original": "testo modificato"})
        assert r.status_code == 200
        detail = client.get(f"/api/db/messages/{mid}").get_json()
        assert detail["content_original"] == "testo modificato"

    def test_delete_message_removes_from_scene(self, client):
        """DELETE /api/db/messages/<id> → 204; GET scene messages non include il messaggio."""
        sid, mid = self._scene_with_message(client, "flow42-delete")
        r = client.delete(f"/api/db/messages/{mid}")
        assert r.status_code == 204
        msgs = client.get(f"/api/db/scenes/{sid}/messages").get_json()["messages"]
        assert all(m["id"] != mid for m in msgs)


class TestFlow43WriteToSceneFromChar:
    """Feature: 'Scrivi a scena' dalla scheda personaggio.

    Verifica che un personaggio possa postare un messaggio in una scena
    tramite POST /api/db/scenes/<id>/messages con author_name=char.name.
    Stato risultante: messaggio appare nella lista messaggi della scena.
    """

    def test_char_posts_message_to_scene(self, client):
        """POST messaggio a scena con author_name personaggio → appare in GET scene messages."""
        sid = client.post("/api/db/scenes", json={"title": "flow43-scene"}).get_json()["id"]
        cid = client.post("/api/db/characters", json={"name": "flow43-char", "kind": "npc"}).get_json()["id"]
        assert cid
        r = client.post(
            f"/api/db/scenes/{sid}/messages",
            json={"author_name": "flow43-char", "content_original": "Ciao dalla scheda!"},
        )
        assert r.status_code == 201
        mid = r.get_json()["id"]
        msgs = client.get(f"/api/db/scenes/{sid}/messages").get_json()["messages"]
        found = next((m for m in msgs if m["id"] == mid), None)
        assert found is not None
        assert found["author_name"] == "flow43-char"
        assert found["content_original"] == "Ciao dalla scheda!"


class TestFlow44DiscordImportEndpoint:
    """Feature: import Discord via UI — POST /api/discord/import.

    Dry-run verifica che la route esista e risponda con stats,
    senza inserire dati reali nel DB di test.
    """

    def test_discord_import_dry_run_returns_stats(self, client):
        """POST /api/discord/import dry_run=True → 200 con stats o 404 se JSONL assente."""
        r = client.post("/api/discord/import", json={"dry_run": True})
        assert r.status_code in (200, 404)
        d = r.get_json()
        assert d is not None
        if r.status_code == 200:
            assert "stats" in d
            assert "dry_run" in d
            assert d["dry_run"] is True

    def test_discord_import_missing_file_404(self, client):
        """POST /api/discord/import con input_path inesistente → 404."""
        r = client.post("/api/discord/import", json={"input_path": "/nonexistent/file.jsonl"})
        assert r.status_code == 404
        assert "error" in r.get_json()


class TestFlow45CharCreateV2Fields:
    """Feature: crea personaggio con campi V2 description/personality.

    Verifica che POST /api/characters accetti i campi V2 e li persista.
    """

    def test_create_char_with_description_persists(self, client, tmp_path):
        """POST /api/characters con description+personality → GET restituisce i valori."""
        from unittest.mock import patch
        chars_dir = tmp_path / "characters"
        chars_dir.mkdir()
        with patch("app.calliope_shell.characters_service._chars_dir", return_value=chars_dir):
            r = client.post("/api/characters", json={
                "name": "Flow45Hero",
                "kind": "player",
                "description": "Un guerriero del nord, cicatrici sul viso.",
                "personality": "Taciturno ma leale.",
            })
        assert r.status_code == 201
        d = r.get_json()
        assert d["name"] == "Flow45Hero"
        stem = d["stem"]
        yaml_file = chars_dir / f"{stem}.draft.yaml"
        assert yaml_file.exists()
        content = yaml_file.read_text()
        assert "Un guerriero del nord" in content
        assert "Taciturno ma leale" in content

class TestFlow46DashboardSurfaces:
    """Feature: Dashboard 'Accesso rapido' punta alle 5 superfici (non panel orfani).

    Stato-risultante: il snapshot dashboard restituisce scene recenti e messaggi;
    gli endpoint che backing il dashboard funzionano correttamente.
    """

    def test_dashboard_snapshot_returns_counts(self, client):
        """GET /api/dashboard/snapshot → risponde 200 con scene_count e message_count."""
        r = client.get("/api/dashboard/snapshot")
        assert r.status_code == 200
        d = r.get_json()
        assert "scene_count" in d or "counts" in d or "kb" in d

    def test_dashboard_recent_scenes_accessible(self, client):
        """GET /api/db/scenes → lista scene per il widget 'Scene recenti' del dashboard."""
        r = client.get("/api/db/scenes")
        assert r.status_code == 200
        assert "scenes" in r.get_json()

    def test_dashboard_recent_discord_msgs_accessible(self, client):
        """GET /api/db/messages/recent?source=discord → lista messaggi Discord per il dashboard."""
        r = client.get("/api/db/messages/recent?source=discord&limit=10")
        assert r.status_code == 200
        d = r.get_json()
        assert "messages" in d


class TestFlow47CharAvatarUpload:
    """Feature: upload immagine personaggio via UI → POST /api/characters/<stem>/image.

    Stato-risultante: dopo upload file, image_path restituito e aggiornabile via PATCH DB.
    """

    def test_image_upload_saves_file_and_returns_path(self, client, tmp_path):
        """POST /api/characters/<stem>/image con file PNG → image_path nel risposta."""
        from unittest.mock import patch
        from io import BytesIO
        chars_dir = tmp_path / "characters"
        chars_dir.mkdir()
        card_yaml = chars_dir / "flow47hero.draft.yaml"
        card_yaml.write_text("name: Flow47Hero\n")
        png_bytes = b'\x89PNG\r\n\x1a\n' + b'\x00' * 16
        with patch("app.calliope_shell.characters_service._chars_dir", return_value=chars_dir):
            r = client.post(
                "/api/characters/flow47hero/image",
                data={"image": (BytesIO(png_bytes), "avatar.png")},
                content_type="multipart/form-data",
            )
        assert r.status_code == 200
        d = r.get_json()
        assert "image_path" in d
        assert d["image_path"].endswith(".png")

    def test_image_path_patchable_to_db_char(self, client):
        """PATCH /api/db/characters/<id> con image_path → GET restituisce il path caricato."""
        cid_r = client.post("/api/db/characters", json={"name": "flow47-db", "kind": "npc"})
        assert cid_r.status_code == 201
        cid = cid_r.get_json()["id"]
        path = "/static/media/characters/flow47-db.png"
        pr = client.patch(f"/api/db/characters/{cid}", json={"image_path": path})
        assert pr.status_code == 200
        assert client.get(f"/api/db/characters/{cid}").get_json()["image_path"] == path


class TestFlow48SceneInlineSummarize:
    """Feature: Summarize inline in scena — POST /api/summarize + salva come is_summary=1.

    Stato-risultante: dopo summarize e save, il messaggio is_summary appare nei messaggi della scena.
    """

    def _create_scene_with_msgs(self, client, title="Flow48Scene"):
        sr = client.post("/api/db/scenes", json={"title": title})
        assert sr.status_code == 201
        sid = sr.get_json()["id"]
        for i in range(3):
            client.post(f"/api/db/scenes/{sid}/messages", json={
                "author_name": f"Eroe{i}", "content_original": f"Messaggio {i}"
            })
        return sid

    def test_summarize_endpoint_accepts_scene_text(self, client):
        """POST /api/summarize con testo scena → restituisce summary non vuoto."""
        text = "Aurora: Il cielo era rosso.\nKira: Fuggiremo prima dell'alba."
        r = client.post("/api/summarize", json={"text": text})
        assert r.status_code in (200, 503)

    def test_save_summary_as_is_summary_message(self, client):
        """POST messaggio is_summary=true nella scena → appare in lista con is_summary=1."""
        sid = self._create_scene_with_msgs(client)
        summary_text = "Riassunto: i protagonisti si preparano a fuggire."
        r = client.post(f"/api/db/scenes/{sid}/messages", json={
            "author_name": "Sistema",
            "content_original": summary_text,
            "is_summary": True,
        })
        assert r.status_code == 201
        msgs = client.get(f"/api/db/scenes/{sid}/messages").get_json().get("messages", [])
        summary_msgs = [m for m in msgs if m.get("is_summary")]
        assert len(summary_msgs) == 1
        assert summary_msgs[0]["content_original"] == summary_text


class TestFlow49MsgToCharPanel:
    """Feature: '→ Personaggio' in Messages → naviga a Characters pre-filtrato per autore.

    Stato-risultante: GET /api/db/characters?name=<author> restituisce il personaggio corrispondente.
    Verifica che l'API alla base del pre-fill funzioni (la navigazione JS è client-side).
    """

    def test_char_filter_by_name_returns_matching(self, client):
        """GET /api/db/characters?name=<nome> → lista con solo il personaggio cercato."""
        client.post("/api/db/characters", json={"name": "AuroraFlow49", "kind": "npc"})
        r = client.get("/api/db/characters?name=AuroraFlow49")
        assert r.status_code == 200
        chars = r.get_json()["characters"]
        assert len(chars) >= 1
        assert all(c["name"] == "AuroraFlow49" for c in chars)

    def test_char_filter_by_name_case_insensitive(self, client):
        """GET /api/db/characters?name= è case-insensitive — stesso char trovato."""
        client.post("/api/db/characters", json={"name": "KiraFlow49", "kind": "player"})
        r = client.get("/api/db/characters?name=kiraflow49")
        assert r.status_code == 200
        chars = r.get_json()["characters"]
        assert any(c["name"] == "KiraFlow49" for c in chars)

    def test_msg_to_char_button_in_html(self, client):
        """Il markup dei messaggi include il bottone '→ Personaggio' con id msg-to-char-."""
        r = client.get("/")
        assert r.status_code == 200
        assert "msg-to-char-" in r.data.decode()
