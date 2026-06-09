"""
Contract test (father-authored acceptance) — WI-10.

Il worker Efesto deve far passare questi test modificando SOLO il blocco
<nav> in `app/calliope_shell/templates/shell.html`:

    - Ridurre le voci <a onclick="showView(...)"> a ≤5
    - Assicurarsi che draft/refine/smartdraft/summarize/translate/arc
      NON compaiano come voci top-level nel <nav>

NON modificare le assertion: sono il contratto di accettazione.
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

# Voci che NON devono mai essere top-level (sono shortcut / in-scene actions)
FORBIDDEN_IN_NAV = {
    "draft",
    "refine",
    "smartdraft",
    "summarize",
    "translate",
    "arc",
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

def test_nav_at_most_five_items(nav_items):
    """Massimo 5 voci top-level nel nav."""
    assert len(nav_items) <= 5, (
        f"Nav ha {len(nav_items)} voci ({nav_items}), atteso ≤5. "
        "Rimuovere almeno una voce (es. 'home') dal blocco <nav>."
    )


def test_legacy_tools_not_in_nav(nav_items):
    """draft/refine/smartdraft/summarize/translate/arc non devono essere top-level."""
    present = FORBIDDEN_IN_NAV & set(nav_items)
    assert not present, (
        f"Voci tool legacy ancora nel nav top-level: {present}. "
        "Spostarle in shortcut-grid o welcome-cards."
    )
