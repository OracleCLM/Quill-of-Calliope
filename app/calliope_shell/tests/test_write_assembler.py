"""M-B tests — assemblatore-prompt condiviso + /api/write + cap adattivo.

VERIFY REALE:
(a) /api/write dispatcha ogni action;
(b) l'assemblatore è condiviso (stesso contesto per genera e rifinisci, stesso input);
(c) il cap adattivo tronca col modello giusto (modello ctx-piccolo → permanent troncato per priorità);
(d) le route legacy rispondono ancora.
"""
from __future__ import annotations

import json

import pytest


# --------------------------------------------------------------------------- #
# Fixture DB temporaneo con schema + 1 char attivo in scena
# --------------------------------------------------------------------------- #

@pytest.fixture()
def db_env(tmp_path, monkeypatch):
    db_path = tmp_path / "test_calliope.db"
    monkeypatch.setenv("CALLIOPE_DB_PATH", str(db_path))
    from app.db import get_db, init_schema, new_id
    from app.db.characters import (
        add_character, add_character_to_scene, save_card_v2, empty_card_v2,
    )

    conn = get_db(str(db_path))
    init_schema(conn)

    # scena minima
    scene_id = new_id()
    conn.execute(
        "INSERT INTO scenes (id, title) VALUES (?, ?)",
        (scene_id, "Test Scene"),
    )
    conn.commit()

    # personaggio con Card V2 ricca
    char_id = add_character(conn, name="Aria", kind="npc")
    card = empty_card_v2("Aria")
    card["data"]["description"] = "A wandering elven bard with silver hair."
    card["data"]["personality"] = "Witty, melancholic, fiercely loyal."
    card["data"]["scenario"] = "The tavern at the edge of the Whispering Woods."
    card["data"]["mes_example"] = "Aria: 'Songs outlast empires, friend.'"
    card["data"]["system_prompt"] = "Always render Aria's dialogue in elegant prose."
    card["data"]["post_history_instructions"] = "Never break character. Stay in-world."
    card["data"]["extensions"]["calliope"] = {
        "speech_pattern": {"pov": "first", "vocabulary": "archaic"},
        "backstory": "Exiled from the Moonspire court.",
    }
    save_card_v2(conn, "Aria", card)
    add_character_to_scene(conn, scene_id, char_id, "participant")
    conn.commit()
    conn.close()
    return {"scene_id": scene_id, "db_path": str(db_path)}


@pytest.fixture()
def client(db_env):
    from app.calliope_shell.server import create_app
    app, _ = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class _MockResp:
    def __init__(self, text):
        self._text = text
        self.status_code = 200

    def json(self):
        return {"result": self._text}

    def raise_for_status(self):
        return None


# --------------------------------------------------------------------------- #
# (a) /api/write dispatcha ogni action
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("action,payload,reply", [
    ("genera", {"intent_it": "Aria entra nella taverna."}, "Aria stepped in."),
    ("continua", {"intent_it": "vai avanti"}, "The fire crackled."),
    ("rifinisci", {"text": "She walks in."}, "She glided in."),
    ("traduci", {"text": "Ciao mondo", "direction": "IT_to_EN"}, "Hello world"),
    ("riassumi", {"text": "A long tale of woe and wonder."}, '{"summary":"woe","key_facts":[]}'),
    ("coerenza", {"text": "Aria has red hair."}, '{"coherent":true,"issues":[]}'),
])
def test_write_dispatches_every_action(client, db_env, monkeypatch, action, payload, reply):
    from app.calliope_shell import write_routes

    monkeypatch.setattr(write_routes.requests, "post",
                        lambda *a, **k: _MockResp(reply))
    body = {"action": action, "scene_id": db_env["scene_id"], **payload}
    r = client.post("/api/write", json=body)
    assert r.status_code == 200, r.get_data(as_text=True)
    data = r.get_json()
    assert data["action"] == action


def test_write_rejects_unknown_action(client):
    r = client.post("/api/write", json={"action": "frobnicate"})
    assert r.status_code == 400


# --------------------------------------------------------------------------- #
# (b) assemblatore condiviso: stesso contesto per genera e rifinisci
# --------------------------------------------------------------------------- #

def test_assembler_shared_same_context(db_env):
    """genera e rifinisci sullo stesso scene/char producono lo STESSO contesto
    permanente (system + char_blocks + post_history)."""
    from app.db import get_db
    from app.calliope_shell.prompt_assembler import assemble

    conn = get_db(db_env["db_path"])
    ctx_a = assemble(conn=conn, active_char_names=["Aria"],
                     user_text="intento A", verb_instruction="VERB-A", model="gpt-oss-120b")
    ctx_b = assemble(conn=conn, active_char_names=["Aria"],
                     user_text="intento B", verb_instruction="VERB-B", model="gpt-oss-120b")
    conn.close()

    # Stesso blocco-permanente (system + schede + post-history): NON dipende dal verbo.
    assert ctx_a.system == ctx_b.system
    assert ctx_a.char_blocks == ctx_b.char_blocks
    assert ctx_a.post_history == ctx_b.post_history
    # I campi SSOT Card V2 sono dentro il contesto.
    blob = "\n".join(ctx_a.char_blocks)
    assert "silver hair" in blob
    assert "archaic" in blob  # speech_pattern da extensions.calliope
    assert "Moonspire" in blob  # backstory da extensions.calliope
    assert "elegant prose" in ctx_a.system  # data.system_prompt
    assert "break character" in ctx_a.post_history  # post_history_instructions


# --------------------------------------------------------------------------- #
# (c) cap adattivo tronca col modello giusto, per priorità
# --------------------------------------------------------------------------- #

def test_cap_adaptive_per_model():
    from app.calliope_shell.budget_adaptive import permanent_cap_for, context_window_for

    # modello grande > modello piccolo
    assert context_window_for("zai-glm-4.7") == 200_000
    assert context_window_for("dolphin-mistral:7b") == 32_000
    assert permanent_cap_for("zai-glm-4.7") > permanent_cap_for("dolphin-mistral:7b")
    # floor 2.5k rispettato per modelli ignoti
    assert permanent_cap_for("modello-ignoto") >= 2500


def test_truncation_priority_drops_memory_then_lore_before_chars():
    """Con cap forzato basso (floor 2.5k) e blocchi enormi, l'ordine di drop è:
    memory → lore → (compressione) char. Le schede char NON spariscono."""
    from app.calliope_shell.budget_adaptive import truncate_permanent, PERMANENT_FLOOR

    big = "word " * 4000  # ~5000 token ciascuno > floor 2.5k
    char_blocks = ["[Aria] " + big]
    lore_blocks = [big, big]
    memory_blocks = [big, big]

    cb, lb, mb, tel = truncate_permanent(
        char_blocks=char_blocks, lore_blocks=lore_blocks,
        memory_blocks=memory_blocks, model="dolphin-mistral:7b",
    )
    assert tel["applied"] is True
    # memory droppata per prima e completamente (priorità MIN)
    assert tel["dropped_memory"] == 2
    assert mb == []
    # lore droppata dopo
    assert tel["dropped_lore"] >= 1
    # char-attivi MAI droppato per intero (almeno 1 scheda sopravvive)
    assert len(cb) >= 1
    assert "[Aria]" in cb[0]
    # blocco-permanente finale entro il cap (floor)
    assert tel["permanent_tokens_after"] <= max(tel["permanent_cap"], PERMANENT_FLOOR)


def test_large_model_no_truncation():
    """Modello a ctx grande NON tronca un blocco-permanente moderato."""
    from app.calliope_shell.budget_adaptive import truncate_permanent

    blk = "word " * 200  # ~250 token
    cb, lb, mb, tel = truncate_permanent(
        char_blocks=[blk], lore_blocks=[blk], memory_blocks=[blk],
        model="zai-glm-4.7",
    )
    assert tel["applied"] is False


# --------------------------------------------------------------------------- #
# (d) route legacy ancora funzionanti
# --------------------------------------------------------------------------- #

def test_legacy_translate_still_works(client, monkeypatch):
    import app.calliope_shell.server as srv
    monkeypatch.setattr(srv.requests, "post", lambda *a, **k: _MockResp("Hello world"))
    r = client.post("/api/translate", json={"text": "Ciao mondo", "direction": "IT_to_EN"})
    assert r.status_code == 200
    assert r.get_json()["translation"] == "Hello world"


def test_legacy_summarize_still_works(client, monkeypatch):
    import app.calliope_shell.server as srv
    monkeypatch.setattr(srv.requests, "post",
                        lambda *a, **k: _MockResp(json.dumps({"summary": "s", "key_facts": []})))
    r = client.post("/api/summarize", json={"text": "Some long text here."})
    assert r.status_code == 200
    assert "summary" in r.get_json()


def test_legacy_draft_still_works(client, db_env, monkeypatch):
    import app.calliope_shell.server as srv
    monkeypatch.setattr(srv.requests, "post", lambda *a, **k: _MockResp("Draft prose."))
    r = client.post("/api/draft", json={"intent_it": "Aria entra", "scene_id": db_env["scene_id"]})
    assert r.status_code == 200
    assert "draft_text" in r.get_json()
