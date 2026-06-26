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
