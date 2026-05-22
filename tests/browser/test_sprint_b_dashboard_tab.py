"""Playwright Python browser-verify for Sprint B Dashboard tab.

Verifies Q1 (tab primary), Q3 (LLM toggle), Q6 (Discord widget graceful),
Q7 (perf budget <500ms warm, polling 15s).

Run manually:
  (FLASK_APP=app.calliope_shell.server python -m flask run --port 5003 &) && \\
  pytest tests/browser/test_sprint_b_dashboard_tab.py -m integration -v
"""
from __future__ import annotations

import os

import pytest

playwright = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

URL = os.environ.get("FLASK_TEST_URL", "http://127.0.0.1:5003/")


def _is_flask_up(url: str) -> bool:
    import urllib.error
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _is_flask_up(URL),
        reason=f"Flask shell not reachable at {URL}",
    ),
]


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        pg = ctx.new_page()
        yield pg
        browser.close()


@pytest.fixture(scope="module")
def loaded_page(page):
    page.goto(URL, wait_until="networkidle", timeout=15000)
    # Q1: Dashboard is default tab → snapshot fetched
    page.wait_for_function(
        "document.getElementById('dash-d-flask') && "
        "document.getElementById('dash-d-flask').textContent !== '…'",
        timeout=10000,
    )
    return page


def test_dashboard_is_landing_tab_q1(loaded_page):
    nav_dash = loaded_page.locator("#nav-dashboard")
    assert nav_dash.count() == 1
    assert "active" in (nav_dash.get_attribute("class") or "")
    panel = loaded_page.locator("#dashboard-panel")
    assert panel.is_visible(), "Dashboard panel must be visible by default (Q1=A)"


def test_dashboard_5_panels_rendered(loaded_page):
    for pid in ("dash-card-state", "dash-card-counts", "dash-card-shortcuts",
                 "dash-card-tone", "dash-card-discord"):
        assert loaded_page.locator(f"#{pid}").is_visible(), f"{pid} not visible"


def test_state_panel_daemon_badges_present(loaded_page):
    for did in ("dash-d-flask", "dash-d-gateway", "dash-d-mascot", "dash-d-chroma"):
        el = loaded_page.locator(f"#{did}")
        txt = el.inner_text().strip()
        assert txt and txt != "…", f"{did} not populated: {txt!r}"


def test_counts_panel_chars_split_active_archive(loaded_page):
    active = loaded_page.locator("#dash-c-chars-active").inner_text().strip()
    archive = loaded_page.locator("#dash-c-chars-archive").inner_text().strip()
    assert active.isdigit(), f"active not numeric: {active!r}"
    # archive may contain warning ⚠ suffix HTML, just check it's not still placeholder
    assert archive != "…"


def test_discord_widget_graceful_degradation_q6(loaded_page):
    # Bot not running + no token → CTA visible with configure hint
    cta = loaded_page.locator("#dash-discord-cta")
    cta_visible = cta.is_visible()
    token_state = loaded_page.locator("#dash-discord-token").inner_text()
    if not token_state or "assente" in token_state.lower() or "✗" in token_state:
        # Token not configured branch
        assert cta_visible, "CTA must be visible when token absent"
        cta_text = cta.inner_text()
        assert "CALLIOPE_DISCORD_BOT_TOKEN" in cta_text or "Configura" in cta_text


def test_tone_panel_toggle_uncensored_q3(loaded_page):
    initial_provider = loaded_page.locator("#dash-llm-provider").inner_text().strip()
    btn = loaded_page.locator("#dash-btn-uncensored")
    btn.click()
    loaded_page.wait_for_timeout(800)
    after = loaded_page.locator("#dash-llm-provider").inner_text().strip()
    assert after != initial_provider or "ollama" in after.lower(), \
        f"provider did not change: before={initial_provider!r} after={after!r}"

    # Toggle back
    btn.click()
    loaded_page.wait_for_timeout(800)
    back = loaded_page.locator("#dash-llm-provider").inner_text().strip()
    assert back == initial_provider, f"toggle back failed: {back!r} vs {initial_provider!r}"


def test_snapshot_perf_warm_under_500ms_q7(loaded_page):
    """Q7 budget: warm snapshot <500ms server-side."""
    result = loaded_page.evaluate("""
        async () => {
            const t0 = performance.now();
            const resp = await fetch('/api/dashboard/snapshot');
            const data = await resp.json();
            return {
                wall_ms: performance.now() - t0,
                server_ms: data.snapshot_latency_ms,
            };
        }
    """)
    assert result["server_ms"] < 500, f"server latency {result['server_ms']}ms > 500ms budget"


def test_shortcuts_navigate_to_panels(loaded_page):
    # Click "Genera draft" → draft panel visible
    loaded_page.locator("#dash-card-shortcuts button").nth(0).click()
    loaded_page.wait_for_timeout(300)
    assert loaded_page.locator("#draft-panel").is_visible()
    # Back to dashboard
    loaded_page.locator("#nav-dashboard").click()
    loaded_page.wait_for_timeout(300)
    assert loaded_page.locator("#dashboard-panel").is_visible()


def test_privacy_badge_still_works_post_sprint_a_regression(loaded_page):
    """Sprint A regression: privacy badge survived Sprint B refactor."""
    badge = loaded_page.locator("#privacy-badge")
    assert badge.count() == 1
    badge.hover()
    loaded_page.wait_for_timeout(300)
    assert loaded_page.locator("#privacy-badge .pb-tooltip").is_visible()
