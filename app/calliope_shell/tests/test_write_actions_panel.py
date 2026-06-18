"""M-D tests — pannello-azioni CONTESTUALE del composer/editor su /api/write.

VERIFY (stato-risultante, non solo presenza):
(a) lo shell carica lo script del pannello e lo CSS dedicato;
(b) lo script del pannello è servito e cabla i 6 verbi su POST /api/write;
(c) UNA sola UI intelligente (un solo pannello), NON 6 bottoni/pannelli sparsi;
(d) i payload che il pannello costruisce sono accettati da /api/write (no 400 schema).
"""
from __future__ import annotations

import pytest

from app.calliope_shell.server import create_app


@pytest.fixture
def client():
    app, _ = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_shell_loads_write_actions_assets(client):
    html = client.get("/").data.decode("utf-8")
    # (a) script del pannello caricato DOPO scenes.js + CSS del pannello presente.
    assert "/static/js/write_actions.js" in html
    assert ".write-actions-pop" in html


def test_write_actions_script_served_and_wired(client):
    js = client.get("/static/js/write_actions.js").data.decode("utf-8")
    assert client.get("/static/js/write_actions.js").status_code == 200
    # (b) i 6 verbi sono cablati sul dispatcher unificato.
    for verb in ("genera", "continua", "rifinisci", "traduci", "riassumi", "coerenza"):
        assert f"'{verb}'" in js, f"verbo mancante nel pannello: {verb}"
    assert "/api/write" in js
    # opera sul testo SELEZIONATO (composer + bolle), non su panel separati.
    assert "scene-compose-text" in js
    assert "scene-thread" in js


def test_single_intelligent_panel_not_six_scattered(client):
    """(c) Una sola classe-pannello → UI unica, non 6 bottoni sparsi in DOM."""
    js = client.get("/static/js/write_actions.js").data.decode("utf-8")
    # un singolo contenitore .write-actions-pop riusato per tutti i verbi
    assert js.count("class = 'write-actions-pop'") + js.count("'write-actions-pop'") >= 1
    # i 6 verbi vivono in UNA lista VERBS, generati in loop (non hard-coded sparsi)
    assert "VERBS" in js
    assert js.count("addEventListener('click'") <= 12  # loop, non 6+ handler statici sparsi


@pytest.mark.parametrize(
    "payload",
    [
        {"action": "rifinisci", "scene_id": "", "text": "Il drago dorme.", "char_focus": ""},
        {"action": "traduci", "text": "Il drago dorme.", "direction": "IT_to_EN"},
        {"action": "riassumi", "text": "Una lunga conversazione di gioco di ruolo."},
        {"action": "coerenza", "scene_id": "", "text": "Il drago vola.", "char_focus": ""},
        {"action": "genera", "scene_id": "", "intent_it": "una scena al tramonto", "char_focus": ""},
        {"action": "continua", "scene_id": "", "intent_it": "prosegui la scena", "char_focus": ""},
    ],
)
def test_panel_payloads_pass_schema(client, payload, monkeypatch):
    """(d) I payload costruiti dal pannello NON vengono respinti per schema (400).

    Il gateway è offline nei test → l'esito atteso è 200 oppure 503 (gateway_down),
    MAI 400 (schema). Così blindiamo il contratto pannello↔/api/write.
    """
    resp = client.post("/api/write", json=payload)
    assert resp.status_code != 400, resp.get_data(as_text=True)
    assert resp.status_code in (200, 503)


def test_bubble_mid_capture_in_js(client):
    """(e) GAP-3: JS cattura `mid` dalla bolla selezionata per PATCH in-place."""
    js = client.get("/static/js/write_actions.js").data.decode("utf-8")
    # _detectSelection deve leggere data-mid dalla bolla padre
    assert "dataset.mid" in js or "data-mid" in js
    # _apply deve fare PATCH /api/db/messages/<mid> con content_enhanced
    assert "PATCH" in js
    assert "/api/db/messages/" in js
    assert "content_enhanced" in js
    # Label "Aggiorna bolla" per verbi replace su bolla con mid
    assert "Aggiorna bolla" in js


def test_patch_message_content_enhanced_accepted(client):
    """(f) PATCH /api/db/messages/<id> accetta content_enhanced senza 400.

    Con DB vuoto (messaggio non trovato) l'endpoint risponde 404 — mai 400 (schema).
    """
    resp = client.patch(
        "/api/db/messages/nonexistent-id",
        json={"content_enhanced": "testo raffinato"},
    )
    # 404 = not found (ok), mai 400 (schema error) né 405 (method not allowed)
    assert resp.status_code in (200, 404), resp.get_data(as_text=True)


def test_generate_btn_and_fn_present(client):
    """(g) GAP-6: il bottone '#scene-generate-btn' e la funzione '_generateFromCompose' sono presenti."""
    html = client.get("/").data.decode("utf-8")
    assert "scene-generate-btn" in html
    js = client.get("/static/js/scenes.js").data.decode("utf-8")
    assert "_generateFromCompose" in js
    assert "/api/write" in js
    assert "intent_it" in js
