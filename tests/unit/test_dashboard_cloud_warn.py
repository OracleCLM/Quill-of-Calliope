"""Regression tests for Sprint C5 — privacy warning per-call (Q4 soft).

Wraps cloud-bound fetch() calls with a modal prompting the operator before
sending data outbound. Modal offers Continue / Cancel + 'don't ask again
per session' checkbox. No hard Lock (per Q4 clarification).
"""
from __future__ import annotations

from pathlib import Path

_TEMPLATE = Path(__file__).parents[2] / "app" / "calliope_shell" / "templates" / "shell.html"
_TRANSLATE_JS = Path(__file__).parents[2] / "app" / "calliope_shell" / "static" / "js" / "translate.js"


def _html() -> str:
    return _TEMPLATE.read_text(encoding="utf-8")


def _translate_js() -> str:
    return _TRANSLATE_JS.read_text(encoding="utf-8")


def test_cloud_warn_modal_html_present():
    html = _html()
    assert 'id="cloud-warn-backdrop"' in html
    assert 'class="cloud-warn-modal"' in html
    assert 'id="cw-btn-continue"' in html
    assert 'id="cw-btn-skip"' in html


def test_modal_has_dont_ask_again_session_checkbox():
    html = _html()
    assert 'id="cw-skip-session"' in html
    assert "Non chiedere più in questa sessione" in html


def test_modal_aria_dialog():
    html = _html()
    assert 'role="dialog"' in html
    assert 'aria-modal="true"' in html


def test_cloud_call_function_defined():
    html = _html()
    assert "function cloudCall" in html


def test_cloud_call_returns_promise():
    html = _html()
    assert "return new Promise" in html


def test_session_silence_flag_present():
    html = _html()
    assert "_cloudWarnSessionSilenced" in html


def test_human_provider_map_has_known_kinds():
    html = _html()
    for kind in ("translate", "refine", "variants", "blend", "next_msg"):
        assert f"'{kind}'" in html


def test_refine_handler_uses_cloud_call():
    html = _html()
    assert "cloudCall('/api/scene/refine'" in html


def test_variants_handler_uses_cloud_call():
    html = _html()
    assert "cloudCall('/api/scene/variants'" in html


def test_blend_handler_uses_cloud_call():
    html = _html()
    assert "cloudCall('/api/scene/blend'" in html


# test_next_msg_handler_uses_cloud_call RIMOSSO (FE-4, 2026-06-11): la funzione
# _generateNextMsg (LLM-gen "continua scena" via cloudCall /api/messages/next) è stata
# rimossa nella migrazione DB scene-as-chat (no retrocompat sul path flat /api/messages).


def test_translate_js_uses_cloud_call_when_available():
    js = _translate_js()
    assert "window.cloudCall" in js
    # Fallback to direct fetch when cloudCall not defined (test harness)
    assert "typeof window.cloudCall === 'function'" in js


def test_cancel_path_rejects_with_known_error():
    html = _html()
    assert "cloud_call_cancelled_by_operator" in html


def test_no_hard_lock_button():
    """Q4 clarification: NO hard Lock blocking, only per-call warning."""
    html = _html()
    # 'Lock' as button label would suggest the rejected hard-lock design
    # (we already have the 🔒 badge from Sprint A2, but no 'Lock' button).
    assert "btn-cloud-lock" not in html
    assert "Privacy Forte" not in html
