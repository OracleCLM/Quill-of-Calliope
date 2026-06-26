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
