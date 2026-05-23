"""Regression tests for Sprint C4 — Dashboard 'Attività recente' panel + 3-mode toggle.

Q5 toggle modes:
  on-demand → fetch only on Refresh click
  highlight → auto-fetch operator-perceived events (default)
  verbose   → auto-fetch all 13 write kinds
"""
from __future__ import annotations

from pathlib import Path

_TEMPLATE = Path(__file__).parents[2] / "app" / "calliope_shell" / "templates" / "shell.html"


def _html() -> str:
    return _TEMPLATE.read_text(encoding="utf-8")


def test_activity_card_panel_present():
    html = _html()
    assert 'id="dash-card-activity"' in html
    assert "Attività recente" in html


def test_activity_card_inside_dashboard_panel():
    html = _html()
    dash_start = html.index('id="dashboard-panel"')
    activity = html.index('id="dash-card-activity"')
    dash_end = html.index('</div>\n\n    <!-- ── MAIN VIEW ── -->')
    assert dash_start < activity < dash_end


def test_three_modes_radio_buttons_present():
    html = _html()
    for mode in ("on-demand", "highlight", "verbose"):
        assert f'value="{mode}"' in html


def test_highlight_is_default_mode():
    html = _html()
    assert 'value="highlight" checked' in html


def test_refresh_button_present():
    html = _html()
    assert 'id="ac-refresh-btn"' in html
    assert "↻ Refresh" in html


def test_load_activity_feed_function_defined():
    html = _html()
    assert "async function loadActivityFeed" in html
    assert "/api/dashboard/activity" in html


def test_activity_mode_helper_defined():
    html = _html()
    assert "function _activityMode" in html


def test_on_demand_blocks_auto_fetch():
    html = _html()
    assert "mode === 'on-demand' && !window._activityForceLoad" in html


def test_activity_polling_30s():
    html = _html()
    assert "30000" in html


def test_activity_list_element_present():
    html = _html()
    assert 'id="activity-list"' in html


def test_activity_item_renders_ts_kind_body():
    html = _html()
    assert 'class="activity-ts"' in html
    assert 'class="activity-kind"' in html
    assert 'class="activity-body"' in html


def test_activity_subject_escaped_against_xss():
    html = _html()
    # detail field is HTML-escaped via replace(/</g, '&lt;')
    assert "replace(/</g, '&lt;')" in html
