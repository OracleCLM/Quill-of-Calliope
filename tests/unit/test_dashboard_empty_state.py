"""Regression tests for Sprint A4 — uniform empty-state UX.

Audit P1 #7: 7 tab had inconsistent empty-state copy. Introduces a
shared `renderEmptyState(targetId, opts)` helper and shared CSS so all
empty / loading / error states look the same across tabs.
"""
from __future__ import annotations

from pathlib import Path

_TEMPLATE = Path(__file__).parents[2] / "app" / "calliope_shell" / "templates" / "shell.html"


def _html() -> str:
    return _TEMPLATE.read_text(encoding="utf-8")


def test_empty_state_css_class_defined():
    html = _html()
    assert ".empty-state" in html
    assert ".es-error" in html
    assert ".es-loading" in html


def test_render_empty_state_helper_defined():
    html = _html()
    assert "window.renderEmptyState" in html


def test_helper_supports_kind_empty_loading_error():
    html = _html()
    assert "'loading'" in html
    assert "'error'" in html


def test_lists_have_data_empty_state_marker():
    html = _html()
    assert 'data-empty-state="scenes"' in html
    assert 'data-empty-state="messages"' in html
    assert 'data-empty-state="arc"' in html


def test_scene_empty_state_uses_helper():
    # FE-0 (2026-06-11): la scene-list JS è stata estratta da shell.html a static/js/scenes.js.
    scenes_js = (
        Path(__file__).parents[2] / "app" / "calliope_shell" / "static" / "js" / "scenes.js"
    ).read_text(encoding="utf-8")
    assert "renderEmptyState('scenes-list'" in scenes_js


# test_messages_empty_state_uses_helper RIMOSSO (FE-4, 2026-06-11): il pannello Messages
# flat-YAML (_loadMessages /api/messages/recent) è stato rimosso nella migrazione DB
# scene-as-chat (no retrocompat). Non esiste più una empty-state 'message-list' da testare.


def test_arc_empty_state_uses_helper():
    html = _html()
    assert "renderEmptyState('arc-ul'" in html


def test_helper_renders_es_icon_title_hint():
    html = _html()
    assert 'class="es-icon"' in html
    assert 'class="es-title"' in html
    assert 'class="es-hint"' in html
