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
