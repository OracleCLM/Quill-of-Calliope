"""Regression tests for Sprint B2 — Dashboard tab + 5 panel template.

Q1 operator-decision = OPZIONE A: nuovo tab "◈ Dashboard" come prima voce nav.
Q6 update = Discord widget code-prepared (graceful-degradation pattern).
"""
from __future__ import annotations

from pathlib import Path

_TEMPLATE = Path(__file__).parents[2] / "app" / "calliope_shell" / "templates" / "shell.html"


def _html() -> str:
    return _TEMPLATE.read_text(encoding="utf-8")


def test_dashboard_panel_present():
    assert 'id="dashboard-panel"' in _html()


def test_dashboard_nav_link_present_and_first():
    html = _html()
    assert 'id="nav-dashboard"' in html
    assert "◈ Dashboard" in html
    # Verify nav-dashboard appears BEFORE nav-scenes in markup order (Q1=A)
    pos_dash = html.index('id="nav-dashboard"')
    pos_scenes = html.index('id="nav-scenes"')
    assert pos_dash < pos_scenes, "nav-dashboard must be first nav item"


def test_dashboard_nav_active_by_default():
    html = _html()
    # Q1: Dashboard is landing tab — active class on nav-dashboard
    assert 'id="nav-dashboard" class="active"' in html


def test_dashboard_has_5_panels():
    html = _html()
    for panel_id in ("dash-card-state", "dash-card-counts", "dash-card-shortcuts",
                      "dash-card-tone", "dash-card-discord"):
        assert f'id="{panel_id}"' in html, f"missing panel: {panel_id}"


def test_panel_state_lists_4_daemons():
    html = _html()
    for daemon_id in ("dash-d-flask", "dash-d-gateway", "dash-d-mascot", "dash-d-chroma"):
        assert f'id="{daemon_id}"' in html


def test_panel_counts_splits_chars_active_archive():
    html = _html()
    assert 'id="dash-c-chars-active"' in html
    assert 'id="dash-c-chars-archive"' in html
    assert "Personaggi attivi" in html
    assert "Personaggi archivio" in html


def test_panel_shortcuts_has_5_surface_buttons():
    html = _html()
    for sc_id in ("shortcut-scenes", "shortcut-characters",
                  "shortcut-lorekb", "shortcut-messages", "shortcut-import"):
        assert f'id="{sc_id}"' in html


def test_panel_tone_has_provider_and_uncensored_switch():
    html = _html()
    assert 'id="dash-llm-provider"' in html
    assert 'id="dash-btn-uncensored"' in html
    assert "Ollama uncensored" in html


def test_panel_discord_code_prepared_with_cta():
    """Q6 update: widget present + CTA placeholder for inactive state."""
    html = _html()
    assert 'id="dash-discord-state"' in html
    assert 'id="dash-discord-token"' in html
    assert 'id="dash-discord-channels"' in html
    assert 'id="dash-discord-lastmsg"' in html
    assert 'id="dash-discord-cta"' in html


def test_dashboard_snapshot_polling_15s():
    """Q7 operator-mandate: refresh polling 15s (NOT WebSocket)."""
    html = _html()
    assert "setInterval" in html
    assert "15000" in html


def test_dashboard_routing_includes_in_all_panels():
    html = _html()
    assert "_ALL_PANELS = ['dashboard'" in html


def test_dashboard_loads_snapshot_on_show():
    html = _html()
    assert "loadDashboardSnapshot" in html
    assert "/api/dashboard/snapshot" in html
