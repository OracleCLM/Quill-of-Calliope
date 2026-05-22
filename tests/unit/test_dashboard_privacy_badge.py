"""Regression test: shell.html must surface privacy 'local-only' badge.

VISION invariant: privacy local-only is a hard mandate. UI must give
operator visible reassurance.
"""
from __future__ import annotations

from pathlib import Path

_TEMPLATE = Path(__file__).parents[2] / "app" / "calliope_shell" / "templates" / "shell.html"


def test_privacy_badge_element_present():
    html = _TEMPLATE.read_text(encoding="utf-8")
    assert 'id="privacy-badge"' in html
    assert 'class="privacy-badge"' in html


def test_privacy_badge_has_lock_icon_and_label():
    html = _TEMPLATE.read_text(encoding="utf-8")
    assert "🔒" in html
    assert "local-only" in html.lower()


def test_privacy_badge_tooltip_mentions_no_cloud_upload():
    html = _TEMPLATE.read_text(encoding="utf-8")
    assert "NO cloud upload" in html
    assert "ChromaDB" in html
    assert "SQLite" in html


def test_privacy_badge_aria_label():
    html = _TEMPLATE.read_text(encoding="utf-8")
    assert 'aria-label="Privacy: local-only' in html


def test_privacy_badge_lists_llm_providers_as_ephemeral():
    html = _TEMPLATE.read_text(encoding="utf-8")
    for provider in ("Cerebras", "Groq", "OpenRouter", "Ollama"):
        assert provider in html
    assert "ephemeral" in html.lower()
