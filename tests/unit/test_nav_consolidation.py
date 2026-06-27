"""
Contract test — WI-10 aggiornato per SPEC-MINIME-UI (approvate 2026-06-27).

SPEC-6: 'arc' è ora 6° tab top-level (rimosso da FORBIDDEN_IN_NAV).
SPEC-1: 'tools' (Strumenti) è il 7° tab top-level.
Limite massimo aggiornato a 7 (5 base + arc + tools).
draft/refine/smartdraft/summarize/translate restano fuori dalla nav top-level.
"""
import re
from pathlib import Path

import pytest

SHELL_HTML = (
    Path(__file__).parents[2]
    / "app"
    / "calliope_shell"
    / "templates"
    / "shell.html"
)

# Voci che NON devono mai essere top-level (sono shortcut / in-scene actions).
# SPEC-6 (2026-06-27): 'arc' rimosso — è ora 6° tab top-level approvato.
FORBIDDEN_IN_NAV = {
    "draft",
    "refine",
    "smartdraft",
    "summarize",
    "translate",
}


def _nav_views(html: str) -> list[str]:
    """Estrae i nomi showView() dalle <a> nel primo blocco <nav>."""
    nav_match = re.search(r"<nav>(.*?)</nav>", html, re.DOTALL)
    if not nav_match:
        return []
    nav_block = nav_match.group(1)
    return re.findall(r"""<a\b[^>]*onclick=["']showView\('([^']+)'\)["']""", nav_block)


@pytest.fixture(scope="module")
def nav_items():
    assert SHELL_HTML.exists(), f"shell.html non trovato: {SHELL_HTML}"
    html = SHELL_HTML.read_text(encoding="utf-8")
    views = _nav_views(html)
    assert views, "Nessuna voce <a showView> trovata nel blocco <nav> — struttura cambiata?"
    return views


# --- WI-10 gate ----------------------------------------------------------

def test_nav_at_most_seven_items(nav_items):
    """Massimo 7 voci top-level nel nav (SPEC-1 + SPEC-6 aggiungono arc + tools)."""
    assert len(nav_items) <= 7, (
        f"Nav ha {len(nav_items)} voci ({nav_items}), atteso ≤7. "
        "Rimuovere le voci in eccesso dal blocco <nav>."
    )


def test_legacy_tools_not_in_nav(nav_items):
    """draft/refine/smartdraft/summarize/translate non devono essere top-level."""
    present = FORBIDDEN_IN_NAV & set(nav_items)
    assert not present, (
        f"Voci tool legacy ancora nel nav top-level: {present}. "
        "Spostarle in shortcut-grid o welcome-cards."
    )
