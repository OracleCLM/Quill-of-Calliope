"""Test strutturali per il panel scenes in shell.html — P6 refinements.

Verifica presenza: filtro arc dropdown, arc badge nel detail header.
"""
from __future__ import annotations

from pathlib import Path

_TEMPLATE = Path(__file__).parents[2] / "app" / "calliope_shell" / "templates" / "shell.html"


def _html() -> str:
    return _TEMPLATE.read_text(encoding="utf-8")


def test_scene_arc_filter_dropdown_present():
    """P6: il dropdown filtro-arco deve esistere nel panel scenes."""
    html = _html()
    assert 'id="scene-arc-filter"' in html


def test_scene_arc_filter_calls_scenesArcFilter():
    """P6: onchange del dropdown deve invocare _scenesArcFilter."""
    html = _html()
    assert "_scenesArcFilter" in html


def test_scene_arc_badge_element_present():
    """P6: il badge arc nell'header del detail deve esistere nel DOM."""
    html = _html()
    assert 'id="scene-arc-badge"' in html


def test_scene_arc_filter_inside_scenes_panel():
    """P6: il filtro arc deve essere DENTRO il panel scenes (ordine markup)."""
    html = _html()
    pos_panel = html.index('id="scenes-panel"')
    pos_filter = html.index('id="scene-arc-filter"')
    pos_detail = html.index('id="scenes-detail-col"')
    assert pos_panel < pos_filter < pos_detail, "arc-filter deve essere nella colonna lista, non nel detail"


def test_nav_parent_map_defined():
    """P6: _NAV_PARENT esiste per panel secondari; arc è ora top-level (SPEC-6)."""
    html = _html()
    assert "_NAV_PARENT" in html
    # arc è top-level tab dal SPEC-6 (2026-06-27) — non più figlio di scenes
    assert "arc:'scenes'" not in html and "arc: 'scenes'" not in html, (
        "arc non deve essere child di scenes (SPEC-6: tab top-level)"
    )


def test_nav_parent_covers_secondary_panels():
    """P6: i panel senza nav link hanno un parent mappato."""
    html = _html()
    for panel in ("draft", "refine", "smartdraft", "summarize", "lorecheck"):
        assert panel in html, f"panel {panel} non trovato nel _NAV_PARENT"


def test_scene_edit_form_present():
    """P6: il form inline di modifica scena deve esistere nel DOM."""
    assert 'id="scene-edit-form"' in _html()


def test_scene_edit_form_has_arc_select():
    """P6: il form di modifica deve includere il select per l'arco."""
    assert 'id="scene-edit-arc"' in _html()


def test_scene_edit_form_has_title_and_location():
    """P6: il form di modifica deve avere campi title e location."""
    html = _html()
    assert 'id="scene-edit-title"' in html
    assert 'id="scene-edit-location"' in html


def test_scene_edit_toggle_button_present():
    """P6: il pulsante che attiva _toggleSceneEdit deve essere nel panel."""
    html = _html()
    assert "_toggleSceneEdit" in html


def test_scene_edit_save_wires_saveSceneEdit():
    """P6: il pulsante salva nel form chiama _saveSceneEdit."""
    html = _html()
    assert "_saveSceneEdit" in html


# ── ID espliciti sui bottoni principali (aggiunta 2026-06-26) ─────────────────

def test_btn_new_scene_has_id():
    """btn-new-scene ha id esplicito per testabilità Playwright."""
    assert 'id="btn-new-scene"' in _html()


def test_btn_scene_submit_has_id():
    """btn-scene-submit (✓ Crea) ha id esplicito."""
    assert 'id="btn-scene-submit"' in _html()


def test_btn_scene_cancel_has_id():
    """btn-scene-cancel (✕) ha id esplicito."""
    assert 'id="btn-scene-cancel"' in _html()


def test_btn_add_roster_has_id():
    """btn-add-roster (+ Roster) ha id esplicito."""
    assert 'id="btn-add-roster"' in _html()


def test_btn_roster_confirm_has_id():
    """btn-roster-confirm (✓ add) ha id esplicito."""
    assert 'id="btn-roster-confirm"' in _html()


def test_sum_save_to_scene_area_style_unified():
    """sum-save-to-scene-area NON deve avere attributo style duplicato (bug fix)."""
    html = _html()
    # cerca il div e verifica che non ci siano due 'style=' sulla stessa riga con id sum-save
    import re
    matches = re.findall(r'<div[^>]+id="sum-save-to-scene-area"[^>]*>', html)
    assert len(matches) == 1
    # un solo attributo style nel tag
    assert matches[0].count('style=') == 1, f"Doppio attributo style trovato: {matches[0]}"


# ── LoreSearch panel selettori (aggiunta 2026-06-26) ─────────────────────────

def test_loresearch_panel_exists():
    """#loresearch-panel deve esistere nel DOM."""
    assert 'id="loresearch-panel"' in _html()


def test_ls_query_input_has_id():
    """Input LoreSearch ha id #ls-query (NON #loresearch-query)."""
    assert 'id="ls-query"' in _html()


def test_btn_loresearch_has_id():
    """Pulsante LoreSearch ha id #btn-loresearch."""
    assert 'id="btn-loresearch"' in _html()


def test_ls_results_container_present():
    """Container risultati LoreSearch ha id #ls-results."""
    assert 'id="ls-results"' in _html()


def test_ls_status_has_id():
    """#ls-status — status indicator ricerca LoreSearch."""
    assert 'id="ls-status"' in _html()


# ── Translate panel selettori (aggiunta 2026-06-26) ──────────────────────────

def test_translate_panel_exists():
    assert 'id="translate-panel"' in _html()


def test_translate_input_has_id():
    assert 'id="translate-input"' in _html()


def test_translate_output_has_id():
    assert 'id="translate-output"' in _html()


def test_btn_translate_has_id():
    assert 'id="btn-translate"' in _html()


# ── LoreCheck panel selettori (aggiunta 2026-06-26) ──────────────────────────

def test_lorecheck_panel_exists():
    assert 'id="lorecheck-panel"' in _html()


def test_lc_text_input_has_id():
    """Textarea LoreCheck usa #lc-text (NON #lorecheck-input)."""
    assert 'id="lc-text"' in _html()


def test_btn_lorecheck_has_id():
    assert 'id="btn-lorecheck"' in _html()


# ── Draft panel selettori (aggiunta 2026-06-26) ──────────────────────────────

def test_draft_panel_exists():
    assert 'id="draft-panel"' in _html()


def test_btn_draft_generate_has_id():
    assert 'id="btn-draft-generate"' in _html()


def test_btn_draft_blend_has_id():
    assert 'id="btn-draft-blend"' in _html()


# ── Refine panel selettori (aggiunta 2026-06-26) ─────────────────────────────

def test_refine_panel_exists():
    assert 'id="refine-panel"' in _html()


def test_refine_scene_input_has_id():
    """Textarea Refine usa #refine-scene-input (NON #refine-text)."""
    assert 'id="refine-scene-input"' in _html()


def test_btn_refine_has_id():
    assert 'id="btn-refine"' in _html()


# ── Input creazione nuova scena (aggiunta 2026-06-26) ────────────────────────

def test_new_scene_title_input_has_id():
    """#new-scene-title — campo titolo nel form inline crea scena."""
    assert 'id="new-scene-title"' in _html()


# ── Compose area nella scene chat (aggiunta 2026-06-26) ──────────────────────

def test_compose_content_textarea_has_id():
    """#compose-content — textarea compose messaggio."""
    assert 'id="compose-content"' in _html()


def test_compose_author_input_has_id():
    """#compose-author — input autore messaggio."""
    assert 'id="compose-author"' in _html()


def test_compose_who_select_has_id():
    """#compose-who — select chi scrive."""
    assert 'id="compose-who"' in _html()


def test_btn_compose_send_has_id():
    """#btn-compose-send — pulsante Invia messaggio."""
    assert 'id="btn-compose-send"' in _html()


# ── Scene chat thread e continue (aggiunta 2026-06-26) ───────────────────────

def test_chat_thread_container_has_id():
    """#chat-thread — container thread messaggi scena."""
    assert 'id="chat-thread"' in _html()


def test_continue_btn_has_id():
    """#continue-btn — pulsante ▶ Genera prossimo messaggio."""
    assert 'id="continue-btn"' in _html()


def test_scene_ctx_hint_has_id():
    """#scene-ctx-hint — input hint contestuale per generazione."""
    assert 'id="scene-ctx-hint"' in _html()


def test_scene_compose_area_has_id():
    """#scene-compose-area — container compose nuovo messaggio."""
    assert 'id="scene-compose-area"' in _html()


# ── Bottoni _sceneAction e scene-edit (aggiunta 2026-06-26) ──────────────────

def test_btn_scene_edit_toggle_has_id():
    """#btn-scene-edit-toggle — pulsante ✎ Modifica nel detail scena."""
    assert 'id="btn-scene-edit-toggle"' in _html()


def test_btn_scene_edit_save_has_id():
    """#btn-scene-edit-save — pulsante ✓ Salva nel form edit scena."""
    assert 'id="btn-scene-edit-save"' in _html()


def test_btn_scene_edit_cancel_has_id():
    """#btn-scene-edit-cancel — pulsante ✕ nel form edit scena."""
    assert 'id="btn-scene-edit-cancel"' in _html()


def test_btn_scene_action_draft_has_id():
    """#btn-scene-action-draft — pulsante ✦ Draft in azioni scena."""
    assert 'id="btn-scene-action-draft"' in _html()


def test_btn_scene_action_refine_has_id():
    """#btn-scene-action-refine — pulsante ✎ Refine in azioni scena."""
    assert 'id="btn-scene-action-refine"' in _html()


def test_btn_scene_action_translate_has_id():
    """#btn-scene-action-translate — pulsante ⇄ Translate in azioni scena."""
    assert 'id="btn-scene-action-translate"' in _html()


def test_btn_scene_action_summarize_has_id():
    """#btn-scene-action-summarize — pulsante ∑ Summarize in azioni scena."""
    assert 'id="btn-scene-action-summarize"' in _html()


def test_btn_scene_action_lorecheck_has_id():
    """#btn-scene-action-lorecheck — pulsante ⊘ Lore Check in azioni scena."""
    assert 'id="btn-scene-action-lorecheck"' in _html()


def test_btn_char_create_has_id():
    """#btn-char-create — pulsante + Nuovo personaggio nel panel characters."""
    assert 'id="btn-char-create"' in _html()


# ── Bottoni arco e roster (aggiunta 2026-06-26) ───────────────────────────────

def test_btn_arc_new_has_id():
    """#btn-arc-new — pulsante + Nuovo arco nel panel archi."""
    assert 'id="btn-arc-new"' in _html()


def test_btn_arc_submit_new_has_id():
    """#btn-arc-submit-new — pulsante ✓ Crea nel form nuovo arco."""
    assert 'id="btn-arc-submit-new"' in _html()


def test_btn_arc_cancel_new_has_id():
    """#btn-arc-cancel-new — pulsante ✕ nel form nuovo arco."""
    assert 'id="btn-arc-cancel-new"' in _html()


def test_btn_roster_cancel_has_id():
    """#btn-roster-cancel — pulsante ✕ chiusura form add-roster."""
    assert 'id="btn-roster-cancel"' in _html()


# ── SmartDraft panel IDs (aggiunta 2026-06-26) ───────────────────────────────

def test_sd_intent_has_id():
    """#sd-intent — textarea intent SmartDraft."""
    assert 'id="sd-intent"' in _html()


def test_btn_smartdraft_has_id():
    """#btn-smartdraft — pulsante ⚡ Generate Draft."""
    assert 'id="btn-smartdraft"' in _html()


def test_sd_output_has_id():
    """#sd-output — container output SmartDraft."""
    assert 'id="sd-output"' in _html()


def test_btn_sd_save_scene_has_id():
    """#btn-sd-save-scene — pulsante → Salva in scena da SmartDraft."""
    assert 'id="btn-sd-save-scene"' in _html()


def test_sd_status_has_id():
    """#sd-status — status indicator SmartDraft."""
    assert 'id="sd-status"' in _html()


def test_btn_sd_copy_has_id():
    """#btn-sd-copy — pulsante 📋 Copy output SmartDraft."""
    assert 'id="btn-sd-copy"' in _html()


# ── LoreCheck panel IDs completi (aggiunta 2026-06-26) ───────────────────────

def test_lc_output_container_has_id():
    """#lc-output — container risultati LoreCheck."""
    assert 'id="lc-output"' in _html()


def test_lc_verdict_has_id():
    """#lc-verdict — div verdetto LoreCheck."""
    assert 'id="lc-verdict"' in _html()


def test_lc_issues_list_has_id():
    """#lc-issues-list — UL lista problemi LoreCheck."""
    assert 'id="lc-issues-list"' in _html()


def test_lc_status_has_id():
    """#lc-status — status indicator LoreCheck."""
    assert 'id="lc-status"' in _html()


# ── Messages panel IDs statici (aggiunta 2026-06-26) ─────────────────────────

def test_msg_char_filter_has_id():
    """#msg-char-filter — input filtro per personaggio nel panel messages."""
    assert 'id="msg-char-filter"' in _html()


def test_msg_discord_only_has_id():
    """#msg-discord-only — checkbox filtro solo-discord."""
    assert 'id="msg-discord-only"' in _html()


def test_msg_target_scene_has_id():
    """#msg-target-scene — select scena di destinazione per → Scena."""
    assert 'id="msg-target-scene"' in _html()


def test_message_list_has_id():
    """#message-list — container lista messaggi."""
    assert 'id="message-list"' in _html()


# ── LoreKB panel IDs statici (aggiunta 2026-06-26) ───────────────────────────

def test_lorekb_new_btn_has_id():
    """#lorekb-new-btn — pulsante + Nuova voce LoreKB."""
    assert 'id="lorekb-new-btn"' in _html()


def test_lorekb_categories_has_id():
    """#lorekb-categories — container filtri categoria LoreKB."""
    assert 'id="lorekb-categories"' in _html()


def test_lorekb_entries_has_id():
    """#lorekb-entries — lista voci LoreKB."""
    assert 'id="lorekb-entries"' in _html()


def test_lorekb_search_input_has_id():
    """#lorekb-search-input — input ricerca LoreKB."""
    assert 'id="lorekb-search-input"' in _html()


def test_lorekb_search_btn_has_id():
    """#lorekb-search-btn — pulsante Cerca LoreKB."""
    assert 'id="lorekb-search-btn"' in _html()


def test_lorekb_search_results_has_id():
    """#lorekb-search-results — container risultati ricerca LoreKB."""
    assert 'id="lorekb-search-results"' in _html()


# ── Dashboard shortcut IDs — 5 superfici (aggiornato: panel orfani rimossi) ──

def test_shortcut_scenes_has_id():
    """#shortcut-scenes — accesso rapido alla superficie Scene."""
    assert 'id="shortcut-scenes"' in _html()


def test_shortcut_characters_has_id():
    """#shortcut-characters — accesso rapido alla superficie Personaggi."""
    assert 'id="shortcut-characters"' in _html()


def test_shortcut_lorekb_has_id():
    """#shortcut-lorekb — accesso rapido alla superficie Lore KB."""
    assert 'id="shortcut-lorekb"' in _html()


def test_shortcut_messages_has_id():
    """#shortcut-messages — accesso rapido alla superficie Messaggi."""
    assert 'id="shortcut-messages"' in _html()


def test_shortcut_import_has_id():
    """#shortcut-import — importa Discord direttamente dal Dashboard."""
    assert 'id="shortcut-import"' in _html()


# ── Characters panel IDs statici (aggiunta 2026-06-26 P6 round 4) ────────────

def test_char_search_has_id():
    """#char-search — input filtro per nome personaggio."""
    assert 'id="char-search"' in _html()


def test_characters_grid_has_id():
    """#characters-grid — container card personaggi."""
    assert 'id="characters-grid"' in _html()


def test_character_detail_has_id():
    """#character-detail — pannello dettaglio personaggio."""
    assert 'id="character-detail"' in _html()


# ── Arc panel IDs statici (aggiunta 2026-06-26 P6 round 4) ──────────────────

def test_arc_ul_has_id():
    """#arc-ul — lista archi nel pannello arc."""
    assert 'id="arc-ul"' in _html()


def test_arc_new_form_has_id():
    """#arc-new-form — form inline creazione nuovo arco."""
    assert 'id="arc-new-form"' in _html()


def test_arc_new_id_input_has_id():
    """#arc-new-id — input ID per nuovo arco."""
    assert 'id="arc-new-id"' in _html()


def test_arc_new_chars_has_id():
    """#arc-new-chars — input personaggi per nuovo arco."""
    assert 'id="arc-new-chars"' in _html()


def test_arc_detail_content_has_id():
    """#arc-detail-content — div contenuto dettaglio arco."""
    assert 'id="arc-detail-content"' in _html()


def test_arc_detail_empty_has_id():
    """#arc-detail-empty — placeholder vuoto pannello arc."""
    assert 'id="arc-detail-empty"' in _html()


# ── Refine panel IDs statici (aggiunta 2026-06-26 P6 round 4) ────────────────

def test_refine_output_box_has_id():
    """#refine-output-box — output box del refine."""
    assert 'id="refine-output-box"' in _html()


def test_refine_output_row_has_id():
    """#refine-output-row — riga output del refine (contiene output-box)."""
    assert 'id="refine-output-row"' in _html()


# ── SmartDraft panel IDs estesi (2026-06-26 round 5) ─────────────────────────

def test_sd_scene_id_has_id():
    """#sd-scene-id — input ID scena SmartDraft."""
    assert 'id="sd-scene-id"' in _html()


def test_sd_char_focus_has_id():
    """#sd-char-focus — select personaggio focus SmartDraft."""
    assert 'id="sd-char-focus"' in _html()


def test_sd_style_has_id():
    """#sd-style — input stile narrativo SmartDraft."""
    assert 'id="sd-style"' in _html()


def test_btn_sd_lorecheck_has_id():
    """#btn-sd-lorecheck — pulsante ⊘ Lore Check da SmartDraft."""
    assert 'id="btn-sd-lorecheck"' in _html()


# ── Summarize panel IDs (2026-06-26 round 5) ─────────────────────────────────

def test_sum_text_has_id():
    """#sum-text — textarea testo da riassumere (NON #summarize-input)."""
    assert 'id="sum-text"' in _html()


def test_btn_sum_save_to_scene_has_id():
    """#btn-sum-save-to-scene — pulsante → Salva in scena dal Summarize."""
    assert 'id="btn-sum-save-to-scene"' in _html()


def test_summarize_panel_has_id():
    """#summarize-panel — container sezione Summarize."""
    assert 'id="summarize-panel"' in _html()


def test_smartdraft_panel_has_id():
    """#smartdraft-panel — container sezione SmartDraft."""
    assert 'id="smartdraft-panel"' in _html()


def test_sum_output_has_id():
    """#sum-output — container output riassunto."""
    assert 'id="sum-output"' in _html()


def test_sum_status_has_id():
    """#sum-status — status indicator Summarize."""
    assert 'id="sum-status"' in _html()


def test_sd_context_info_has_id():
    """#sd-context-info — info contesto usato nel draft (scene/chars/lore)."""
    assert 'id="sd-context-info"' in _html()


def test_sd_lint_has_id():
    """#sd-lint — container warning lint cliché SmartDraft."""
    assert 'id="sd-lint"' in _html()


def test_sd_actions_has_id():
    """#sd-actions — container pulsanti azione post-draft (copy/save/lorecheck)."""
    assert 'id="sd-actions"' in _html()


# ── Dashboard panel IDs (2026-06-26 round 5) ─────────────────────────────────

def test_dashboard_panel_has_id():
    """#dashboard-panel — container principale dashboard."""
    assert 'id="dashboard-panel"' in _html()


def test_dash_card_state_has_id():
    """#dash-card-state — card stato sistema."""
    assert 'id="dash-card-state"' in _html()


def test_dash_card_counts_has_id():
    """#dash-card-counts — card contatori conoscenza."""
    assert 'id="dash-card-counts"' in _html()


def test_dash_d_flask_has_id():
    """#dash-d-flask — stato servizio Flask nella dashboard."""
    assert 'id="dash-d-flask"' in _html()


def test_dash_c_chars_active_has_id():
    """#dash-c-chars-active — contatore personaggi attivi."""
    assert 'id="dash-c-chars-active"' in _html()


def test_dash_c_scenes_has_id():
    """#dash-c-scenes — contatore scene totali."""
    assert 'id="dash-c-scenes"' in _html()


def test_dash_c_arcs_has_id():
    """#dash-c-arcs — contatore archi narrativi."""
    assert 'id="dash-c-arcs"' in _html()


def test_dash_c_messages_has_id():
    """#dash-c-messages — contatore messaggi totali."""
    assert 'id="dash-c-messages"' in _html()


def test_dash_discord_state_has_id():
    """#dash-discord-state — stato Discord bot nella dashboard."""
    assert 'id="dash-discord-state"' in _html()


def test_dash_snapshot_status_has_id():
    """#dash-snapshot-status — testo status snapshot dashboard."""
    assert 'id="dash-snapshot-status"' in _html()


def test_dash_card_recent_scenes_has_id():
    """#dash-card-recent-scenes — card scene recenti dashboard."""
    assert 'id="dash-card-recent-scenes"' in _html()


# ── Draft panel IDs estesi (2026-06-26 round 5) ───────────────────────────────

def test_draft_prompt_has_id():
    """#draft-prompt — textarea prompt di draft nel panel."""
    assert 'id="draft-prompt"' in _html()


def test_draft_scene_type_has_id():
    """#draft-scene-type — select tipo scena nel panel draft."""
    assert 'id="draft-scene-type"' in _html()


def test_draft_n_variants_has_id():
    """#draft-n-variants — input numero varianti nel panel draft."""
    assert 'id="draft-n-variants"' in _html()


# ── Refine panel IDs estesi (2026-06-26 round 5) ─────────────────────────────

def test_refine_feedback_has_id():
    """#refine-feedback — input feedback utente nel panel refine."""
    assert 'id="refine-feedback"' in _html()


def test_refine_auto_lint_has_id():
    """#refine-auto-lint — checkbox auto-lint nel panel refine."""
    assert 'id="refine-auto-lint"' in _html()


# ── LoreCheck panel IDs estesi (2026-06-26 round 5) ──────────────────────────

def test_lc_scene_id_has_id():
    """#lc-scene-id — input scene ID (opzionale) nel panel LoreCheck."""
    assert 'id="lc-scene-id"' in _html()


# ── Draft panel IDs output/state (2026-06-26 round 5) ────────────────────────

def test_draft_status_has_id():
    """#draft-status — div status/feedback nel panel draft."""
    assert 'id="draft-status"' in _html()


def test_draft_variants_container_has_id():
    """#draft-variants-container — container liste varianti draft."""
    assert 'id="draft-variants-container"' in _html()


def test_draft_variants_list_has_id():
    """#draft-variants-list — UL varianti selezionabili."""
    assert 'id="draft-variants-list"' in _html()


def test_draft_blend_output_has_id():
    """#draft-blend-output — container output blended draft."""
    assert 'id="draft-blend-output"' in _html()


def test_draft_blend_text_has_id():
    """#draft-blend-text — textarea testo blended."""
    assert 'id="draft-blend-text"' in _html()


# ── Scene detail IDs (2026-06-26 round 5) ────────────────────────────────────

def test_scene_detail_has_id():
    """#scene-detail — container detail di una scena."""
    assert 'id="scene-detail"' in _html()


def test_scene_detail_title_has_id():
    """#scene-detail-title — h2 titolo scena nel detail view."""
    assert 'id="scene-detail-title"' in _html()


def test_scene_detail_meta_has_id():
    """#scene-detail-meta — metadati scena (status, chars, messages)."""
    assert 'id="scene-detail-meta"' in _html()


def test_scenes_list_has_id():
    """#scenes-list — UL lista scene nel panel scenes."""
    assert 'id="scenes-list"' in _html()


def test_compose_status_has_id():
    """#compose-status — span status dopo invio messaggio compose."""
    assert 'id="compose-status"' in _html()


# ── Revive panel IDs (2026-06-26 round 6) ────────────────────────────────────

def test_btn_scene_revive_has_id():
    """#btn-scene-revive — pulsante 🔄 Revive Scene nel detail scena."""
    assert 'id="btn-scene-revive"' in _html()


def test_revive_status_has_id():
    """#revive-status — span feedback dopo revive."""
    assert 'id="revive-status"' in _html()


def test_revive_output_has_id():
    """#revive-output — div output testo revivificato."""
    assert 'id="revive-output"' in _html()


# ── Scene filter IDs (2026-06-26 round 6) ────────────────────────────────────

def test_scene_filter_has_id():
    """#scene-filter — input filtro testo per lista scene."""
    assert 'id="scene-filter"' in _html()


# ── Ulteriori IDs scene panel (2026-06-26 round 6) ───────────────────────────

def test_scene_edit_status_has_id():
    """#scene-edit-status — span feedback inline nel form edit scena."""
    assert 'id="scene-edit-status"' in _html()


def test_lorekb_detail_has_id():
    """#lorekb-detail — pannello detail LoreKB (form o info voce)."""
    assert 'id="lorekb-detail"' in _html()


def test_msg_status_has_id():
    """#msg-status — span feedback filtro nel panel messaggi."""
    assert 'id="msg-status"' in _html()


def test_sum_save_status_has_id():
    """#sum-save-status — span feedback salvataggio summary in scena."""
    assert 'id="sum-save-status"' in _html()


# ── Panel container IDs principali (2026-06-26 round 6 batch 2) ──────────────

def test_arc_panel_has_id():
    """#arc-panel — container panel Arc narrativi."""
    assert 'id="arc-panel"' in _html()


def test_arc_list_col_has_id():
    """#arc-list-col — colonna lista archi nel panel."""
    assert 'id="arc-list-col"' in _html()


def test_arc_detail_col_has_id():
    """#arc-detail-col — colonna detail arco."""
    assert 'id="arc-detail-col"' in _html()


def test_arc_detail_title_has_id():
    """#arc-detail-title — h2 titolo arco nel detail view."""
    assert 'id="arc-detail-title"' in _html()


def test_characters_panel_has_id():
    """#characters-panel — container panel Personaggi."""
    assert 'id="characters-panel"' in _html()


def test_messages_panel_has_id():
    """#messages-panel — container panel Messaggi."""
    assert 'id="messages-panel"' in _html()


def test_btn_copy_last_has_id():
    """#btn-copy-last — pulsante 📋 Copia ultimo messaggio."""
    assert 'id="btn-copy-last"' in _html()


def test_btn_copy_scene_has_id():
    """#btn-copy-scene — pulsante 📄 Copia scena intera."""
    assert 'id="btn-copy-scene"' in _html()


def test_btn_scene_smartdraft_has_id():
    """#btn-scene-smartdraft — pulsante SmartDraft rapido nel detail scena."""
    assert 'id="btn-scene-smartdraft"' in _html()


def test_refine_status_has_id():
    """#refine-status — div status feedback nel panel Refine."""
    assert 'id="refine-status"' in _html()


def test_translate_status_has_id():
    """#translate-status — div status nel panel Translate."""
    assert 'id="translate-status"' in _html()


def test_sum_summary_has_id():
    """#sum-summary — div testo del riassunto generato nel panel Summarize."""
    assert 'id="sum-summary"' in _html()


def test_sum_facts_has_id():
    """#sum-facts — ul punti chiave del summary."""
    assert 'id="sum-facts"' in _html()


def test_roster_list_has_id():
    """#roster-list — ul personaggi nel roster di scena."""
    assert 'id="roster-list"' in _html()


def test_new_scene_form_has_id():
    """#new-scene-form — form creazione nuova scena."""
    assert 'id="new-scene-form"' in _html()


def test_scene_empty_state_has_id():
    """#scene-empty-state — div empty state quando nessuna scena è aperta."""
    assert 'id="scene-empty-state"' in _html()


def test_sd_save_status_has_id():
    """#sd-save-status — span feedback salvataggio SmartDraft in scena."""
    assert 'id="sd-save-status"' in _html()


# ── Dashboard IDs secondari (2026-06-26 round 6 batch 3) ─────────────────────

def test_dash_card_activity_has_id():
    """#dash-card-activity — card attività recente dashboard."""
    assert 'id="dash-card-activity"' in _html()


def test_dash_card_discord_has_id():
    """#dash-card-discord — card stato Discord dashboard."""
    assert 'id="dash-card-discord"' in _html()


def test_dash_card_shortcuts_has_id():
    """#dash-card-shortcuts — card shortcut rapidi dashboard."""
    assert 'id="dash-card-shortcuts"' in _html()


def test_dash_d_chroma_has_id():
    """#dash-d-chroma — indicatore stato ChromaDB."""
    assert 'id="dash-d-chroma"' in _html()


def test_dash_d_gateway_has_id():
    """#dash-d-gateway — indicatore stato LLM gateway."""
    assert 'id="dash-d-gateway"' in _html()


def test_dash_d_mascot_has_id():
    """#dash-d-mascot — indicatore stato mascot WS."""
    assert 'id="dash-d-mascot"' in _html()


def test_dash_c_lore_has_id():
    """#dash-c-lore — contatore voci Lore KB dashboard."""
    assert 'id="dash-c-lore"' in _html()


def test_dash_llm_provider_has_id():
    """#dash-llm-provider — span provider LLM corrente dashboard."""
    assert 'id="dash-llm-provider"' in _html()


def test_activity_list_has_id():
    """#activity-list — ul attività recente nel panel dashboard."""
    assert 'id="activity-list"' in _html()


def test_copy_last_status_has_id():
    """#copy-last-status — span feedback 📋 Copia ultimo messaggio."""
    assert 'id="copy-last-status"' in _html()


def test_arc_new_title_has_id():
    """#arc-new-title — input titolo nuova arc nel form creazione."""
    assert 'id="arc-new-title"' in _html()


def test_arc_new_status_has_id():
    """#arc-new-status — span feedback creazione arc."""
    assert 'id="arc-new-status"' in _html()


def test_char_memory_details_has_id():
    """#char-memory-details — div snippets memoria ChromaDB personaggio."""
    assert 'id="char-memory-details"' in _html()


# ── Arc detail IDs (2026-06-26 round 6 batch 4) ──────────────────────────────

def test_arc_btn_summary_has_id():
    """#arc-btn-summary — pulsante genera summary arco."""
    assert 'id="arc-btn-summary"' in _html()


def test_arc_btn_threads_has_id():
    """#arc-btn-threads — pulsante carica thread scene per arco."""
    assert 'id="arc-btn-threads"' in _html()


def test_arc_btn_continue_has_id():
    """#arc-btn-continue — pulsante genera continuazione arco."""
    assert 'id="arc-btn-continue"' in _html()


def test_arc_status_has_id():
    """#arc-status — span feedback operazioni arc."""
    assert 'id="arc-status"' in _html()


def test_arc_summary_box_has_id():
    """#arc-summary-box — div testo summary arco generato."""
    assert 'id="arc-summary-box"' in _html()


def test_arc_threads_list_has_id():
    """#arc-threads-list — div lista thread scene rilevati."""
    assert 'id="arc-threads-list"' in _html()


def test_arc_detail_meta_has_id():
    """#arc-detail-meta — div metadati arco (status, chars, scenes)."""
    assert 'id="arc-detail-meta"' in _html()


def test_arc_detail_scenes_has_id():
    """#arc-detail-scenes — div lista scene associate all'arco."""
    assert 'id="arc-detail-scenes"' in _html()


def test_arc_continue_seed_has_id():
    """#arc-continue-seed — input seed testo per continuazione arco."""
    assert 'id="arc-continue-seed"' in _html()


def test_arc_continue_type_has_id():
    """#arc-continue-type — select tipo continuazione (epilogo, twist, cliffhanger)."""
    assert 'id="arc-continue-type"' in _html()


def test_arc_hint_input_has_id():
    """#arc-hint-input — input hint extra per generazione arc."""
    assert 'id="arc-hint-input"' in _html()


def test_arc_continue_result_has_id():
    """#arc-continue-result — div output testo continuazione generata."""
    assert 'id="arc-continue-result"' in _html()


def test_continue_status_has_id():
    """#continue-status — span feedback generazione continuazione."""
    assert 'id="continue-status"' in _html()


# ── Nav IDs (2026-06-26 round 6 batch 5) ─────────────────────────────────────

def test_nav_dashboard_has_id():
    """#nav-dashboard — link nav Dashboard."""
    assert 'id="nav-dashboard"' in _html()


def test_nav_scenes_has_id():
    """#nav-scenes — link nav Scene."""
    assert 'id="nav-scenes"' in _html()


def test_nav_characters_has_id():
    """#nav-characters — link nav Personaggi."""
    assert 'id="nav-characters"' in _html()


def test_nav_messages_has_id():
    """#nav-messages — link nav Messaggi."""
    assert 'id="nav-messages"' in _html()


def test_nav_lorekb_has_id():
    """#nav-lorekb — link nav Lore KB."""
    assert 'id="nav-lorekb"' in _html()


def test_main_view_has_id():
    """#main-view — container principale viste panel."""
    assert 'id="main-view"' in _html()


def test_mascot_has_id():
    """#mascot — container Live2D mascot (canvas o div)."""
    assert 'id="mascot"' in _html()


# ── Summarize output IDs (2026-06-26 round 6 batch 5) ────────────────────────

def test_btn_summarize_has_id():
    """#btn-summarize — pulsante Genera Summary nel panel Summarize."""
    assert 'id="btn-summarize"' in _html()


def test_sum_meta_has_id():
    """#sum-meta — div metadati summary (word_count, model)."""
    assert 'id="sum-meta"' in _html()


# ── LoreCheck output IDs (2026-06-26 round 6 batch 5) ────────────────────────

def test_lc_issues_has_id():
    """#lc-issues — ul problemi rilevati da LoreCheck."""
    assert 'id="lc-issues"' in _html()


def test_lc_refs_has_id():
    """#lc-refs — ul riferimenti lore trovati da LoreCheck."""
    assert 'id="lc-refs"' in _html()


# ── Refine lint output IDs (2026-06-26 round 6 batch 5) ──────────────────────

def test_refine_lint_badge_has_id():
    """#refine-lint-badge — badge contatore problemi stile dal Refine."""
    assert 'id="refine-lint-badge"' in _html()


def test_refine_lint_list_has_id():
    """#refine-lint-list — ul lista problemi stile lint nel panel Refine."""
    assert 'id="refine-lint-list"' in _html()


# ── SmartDraft output (2026-06-26 round 6 batch 5) ───────────────────────────

def test_gen_output_has_id():
    """#gen-output — div testo generato da SmartDraft."""
    assert 'id="gen-output"' in _html()


# ── Scenes panel sub-IDs (2026-06-26 round 6 batch 5) ────────────────────────

def test_scenes_list_col_has_id():
    """#scenes-list-col — colonna sinistra lista scene nel panel."""
    assert 'id="scenes-list-col"' in _html()


def test_scenes_filter_bar_has_id():
    """#scenes-filter-bar — barra filtri nella colonna lista scene."""
    assert 'id="scenes-filter-bar"' in _html()


def test_new_scene_location_has_id():
    """#new-scene-location — input location nel form nuova scena."""
    assert 'id="new-scene-location"' in _html()


def test_new_scene_status_has_id():
    """#new-scene-status — span feedback creazione nuova scena."""
    assert 'id="new-scene-status"' in _html()


def test_lorekb_panel_has_id():
    """#lorekb-panel — container panel Lore KB."""
    assert 'id="lorekb-panel"' in _html()


def test_scene_char_select_has_id():
    """#scene-char-select — select personaggio per compose nel detail scena."""
    assert 'id="scene-char-select"' in _html()


# ── Roster form IDs (2026-06-26 round 6 batch 5) ─────────────────────────────

def test_add_roster_form_has_id():
    """#add-roster-form — form aggiunta personaggio al roster di scena."""
    assert 'id="add-roster-form"' in _html()


def test_add_roster_char_sel_has_id():
    """#add-roster-char-sel — select personaggio nel form roster."""
    assert 'id="add-roster-char-sel"' in _html()


def test_add_roster_role_sel_has_id():
    """#add-roster-role-sel — select ruolo nel form roster."""
    assert 'id="add-roster-role-sel"' in _html()


def test_add_roster_status_has_id():
    """#add-roster-status — span feedback aggiunta al roster."""
    assert 'id="add-roster-status"' in _html()


# ── Characters list panel IDs (2026-06-26 round 6 batch 6) ───────────────────

def test_char_list_has_id():
    """#char-list — ul lista personaggi nel char-list-panel."""
    assert 'id="char-list"' in _html()


def test_char_list_panel_has_id():
    """#char-list-panel — container lista personaggi sidebar."""
    assert 'id="char-list-panel"' in _html()


# ── Activity + Draft IDs (2026-06-26 round 6 batch 6) ────────────────────────

def test_ac_refresh_btn_has_id():
    """#ac-refresh-btn — pulsante aggiorna counters/activity."""
    assert 'id="ac-refresh-btn"' in _html()


def test_draft_n_label_has_id():
    """#draft-n-label — label numero varianti da generare nel panel Draft."""
    assert 'id="draft-n-label"' in _html()


def test_scenes_continue_area_has_id():
    """#scenes-continue-area — area bottoni continua scena nel detail."""
    assert 'id="scenes-continue-area"' in _html()


# ── Dashboard Discord + LLM IDs (2026-06-26 round 6 batch 6) ─────────────────

def test_dash_card_tone_has_id():
    """#dash-card-tone — card tone/voice settings dashboard."""
    assert 'id="dash-card-tone"' in _html()


def test_dash_discord_channels_has_id():
    """#dash-discord-channels — div canali Discord monitorati."""
    assert 'id="dash-discord-channels"' in _html()


def test_dash_recent_scenes_list_has_id():
    """#dash-recent-scenes-list — ul scene recenti nella card dashboard."""
    assert 'id="dash-recent-scenes-list"' in _html()


def test_dash_c_chars_archive_has_id():
    """#dash-c-chars-archive — contatore personaggi in archivio (non attivi)."""
    assert 'id="dash-c-chars-archive"' in _html()


def test_dash_llm_model_has_id():
    """#dash-llm-model — span modello LLM corrente dashboard."""
    assert 'id="dash-llm-model"' in _html()


def test_dash_card_recent_discord_has_id():
    """#dash-card-recent-discord — card messaggi Discord recenti dashboard."""
    assert 'id="dash-card-recent-discord"' in _html()


def test_dash_recent_discord_list_has_id():
    """#dash-recent-discord-list — ul messaggi Discord recenti."""
    assert 'id="dash-recent-discord-list"' in _html()


def test_dash_discord_cta_has_id():
    """#dash-discord-cta — area call-to-action per configurare Discord."""
    assert 'id="dash-discord-cta"' in _html()


def test_dash_discord_lastmsg_has_id():
    """#dash-discord-lastmsg — span ultimo messaggio Discord ricevuto."""
    assert 'id="dash-discord-lastmsg"' in _html()


def test_dash_discord_token_has_id():
    """#dash-discord-token — span stato token Discord bot."""
    assert 'id="dash-discord-token"' in _html()


# ── Cloud warning modal IDs (2026-06-26 round 6 batch 6) ─────────────────────

def test_cloud_warn_backdrop_has_id():
    """#cloud-warn-backdrop — backdrop modale avviso cloud LLM."""
    assert 'id="cloud-warn-backdrop"' in _html()


def test_cw_title_has_id():
    """#cw-title — titolo modale avviso cloud."""
    assert 'id="cw-title"' in _html()


def test_cw_detail_has_id():
    """#cw-detail — dettaglio testo modale avviso cloud."""
    assert 'id="cw-detail"' in _html()


def test_cw_provider_has_id():
    """#cw-provider — span nome provider nel modale cloud."""
    assert 'id="cw-provider"' in _html()


def test_cw_btn_continue_has_id():
    """#cw-btn-continue — pulsante Continua nel modale cloud."""
    assert 'id="cw-btn-continue"' in _html()


def test_cw_btn_skip_has_id():
    """#cw-btn-skip — pulsante Salta/Non mostrare nel modale cloud."""
    assert 'id="cw-btn-skip"' in _html()


def test_cw_skip_session_has_id():
    """#cw-skip-session — checkbox non mostrare di nuovo in sessione."""
    assert 'id="cw-skip-session"' in _html()


# ── Misc panel IDs (2026-06-26 round 6 batch 6) ──────────────────────────────

def test_welcome_panel_has_id():
    """#welcome-panel — panel benvenuto (home view)."""
    assert 'id="welcome-panel"' in _html()


def test_privacy_badge_has_id():
    """#privacy-badge — badge 🔒 Local-only visibile nell'header."""
    assert 'id="privacy-badge"' in _html()


def test_st_iframe_has_id():
    """#st-iframe — iframe SillyTavern (integrazione legacy)."""
    assert 'id="st-iframe"' in _html()


def test_cnt_chars_has_id():
    """#cnt-chars — span contatore personaggi nella sidebar counters."""
    assert 'id="cnt-chars"' in _html()


def test_cnt_scenes_has_id():
    """#cnt-scenes — span contatore scene nella sidebar counters."""
    assert 'id="cnt-scenes"' in _html()


def test_cnt_arcs_has_id():
    """#cnt-arcs — span contatore archi nella sidebar counters."""
    assert 'id="cnt-arcs"' in _html()


def test_cnt_lore_has_id():
    """#cnt-lore — span contatore voci lore nella sidebar counters."""
    assert 'id="cnt-lore"' in _html()


def test_counters_sidebar_has_id():
    """#counters-sidebar — div sidebar contatori riassuntivi."""
    assert 'id="counters-sidebar"' in _html()


def test_dash_btn_uncensored_has_id():
    """#dash-btn-uncensored — pulsante toggle modalità uncensored."""
    assert 'id="dash-btn-uncensored"' in _html()


def test_dash_llm_uncensored_has_id():
    """#dash-llm-uncensored — span stato modalità uncensored LLM."""
    assert 'id="dash-llm-uncensored"' in _html()


def test_dash_uncensored_label_has_id():
    """#dash-uncensored-label — label modalità uncensored dashboard."""
    assert 'id="dash-uncensored-label"' in _html()


def test_dash_discord_cta_text_has_id():
    """#dash-discord-cta-text — testo CTA discord nella dashboard."""
    assert 'id="dash-discord-cta-text"' in _html()
