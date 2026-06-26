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
    """P6: _NAV_PARENT mappa panel secondari → nav parent (coerenza navbar)."""
    html = _html()
    assert "_NAV_PARENT" in html
    assert "arc:'scenes'" in html or "arc: 'scenes'" in html


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


# ── Dashboard shortcut IDs (aggiunta 2026-06-26 P6 round 4) ──────────────────

def test_shortcut_draft_has_id():
    """#shortcut-draft — pulsante scorciatoia → panel draft."""
    assert 'id="shortcut-draft"' in _html()


def test_shortcut_refine_has_id():
    """#shortcut-refine — pulsante scorciatoia → panel refine."""
    assert 'id="shortcut-refine"' in _html()


def test_shortcut_translate_has_id():
    """#shortcut-translate — pulsante scorciatoia → panel translate."""
    assert 'id="shortcut-translate"' in _html()


def test_shortcut_arc_has_id():
    """#shortcut-arc — pulsante scorciatoia → panel arc."""
    assert 'id="shortcut-arc"' in _html()


def test_shortcut_smartdraft_has_id():
    """#shortcut-smartdraft — pulsante scorciatoia → panel smartdraft."""
    assert 'id="shortcut-smartdraft"' in _html()


def test_shortcut_summarize_has_id():
    """#shortcut-summarize — pulsante scorciatoia → panel summarize."""
    assert 'id="shortcut-summarize"' in _html()


def test_shortcut_lorecheck_has_id():
    """#shortcut-lorecheck — pulsante scorciatoia → panel lorecheck."""
    assert 'id="shortcut-lorecheck"' in _html()


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
