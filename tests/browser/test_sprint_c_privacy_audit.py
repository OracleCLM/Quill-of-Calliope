"""Playwright Python browser-verify for Sprint C (privacy warning + activity feed).

Covers Q4 (soft warning per-call) + Q5 (write-only activity feed 3 modes).

Run manually:
  (FLASK_APP=app.calliope_shell.server python -m flask run --port 5005 &) && \\
  FLASK_TEST_URL=http://127.0.0.1:5005/ pytest tests/browser/test_sprint_c_privacy_audit.py -v
"""
from __future__ import annotations

import os

import pytest

playwright = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

URL = os.environ.get("FLASK_TEST_URL", "http://127.0.0.1:5005/")


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
    pytest.mark.skipif(not _is_flask_up(URL), reason=f"Flask not reachable at {URL}"),
]


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        pg = ctx.new_page()
        pg.goto(URL, wait_until="networkidle", timeout=15000)
        # Dashboard auto-loads
        pg.wait_for_function(
            "document.getElementById('dash-d-flask') && "
            "document.getElementById('dash-d-flask').textContent !== '…'",
            timeout=10000,
        )
        yield pg
        browser.close()


# ── Sprint C4: Activity feed UI ────────────────────────────────────────────

def test_activity_panel_visible_on_dashboard(page):
    assert page.locator("#dash-card-activity").is_visible()


def test_activity_three_radio_modes(page):
    for mode in ("on-demand", "highlight", "verbose"):
        radio = page.locator(f"input[name='activity-mode'][value='{mode}']")
        assert radio.count() == 1


def test_activity_highlight_default_checked(page):
    is_checked = page.locator("input[name='activity-mode'][value='highlight']").is_checked()
    assert is_checked


def test_activity_on_demand_shows_placeholder(page):
    page.locator("input[name='activity-mode'][value='on-demand']").check()
    page.wait_for_timeout(500)
    text = page.locator("#activity-list").inner_text()
    assert "on-demand" in text.lower() or "refresh" in text.lower()


def test_activity_refresh_button_loads(page):
    page.locator("input[name='activity-mode'][value='on-demand']").check()
    page.wait_for_timeout(300)
    page.locator("#ac-refresh-btn").click()
    page.wait_for_timeout(1000)
    # After refresh, list either shows empty-state or events — both ok
    text = page.locator("#activity-list").inner_text()
    assert text  # non-empty


def test_activity_verbose_mode_loads(page):
    page.locator("input[name='activity-mode'][value='verbose']").check()
    page.wait_for_timeout(1500)
    list_html = page.locator("#activity-list").inner_html()
    # Either has activity-item entries or an empty-state — both ok
    assert "activity-item" in list_html or "Nessuna attività" in list_html or "activity-empty" in list_html


# ── Sprint C5: Cloud warn modal ────────────────────────────────────────────

def test_cloud_warn_backdrop_present_hidden_initially(page):
    backdrop = page.locator("#cloud-warn-backdrop")
    assert backdrop.count() == 1
    assert not backdrop.is_visible()


def test_cloud_warn_helper_defined(page):
    fn = page.evaluate("typeof window.cloudCall")
    assert fn == "function"


def test_cloud_warn_triggers_on_refine_click(page):
    page.locator("#nav-refine").click()
    page.wait_for_timeout(400)
    page.locator("#refine-scene-input").fill("Original scene text.")
    page.locator("#refine-feedback").fill("accorcia")
    page.locator("#btn-refine").click()
    # Modal should appear (visible class added)
    page.wait_for_function(
        "document.getElementById('cloud-warn-backdrop').classList.contains('visible')",
        timeout=3000,
    )
    backdrop = page.locator("#cloud-warn-backdrop")
    assert backdrop.is_visible()


def test_cloud_warn_modal_displays_provider_name(page):
    """After the previous test triggered the modal, provider field is set."""
    provider = page.locator("#cw-provider").inner_text()
    assert "Groq" in provider or "gateway" in provider.lower()


def test_cloud_warn_cancel_closes_modal(page):
    page.locator("#cw-btn-skip").click()
    page.wait_for_function(
        "!document.getElementById('cloud-warn-backdrop').classList.contains('visible')",
        timeout=2000,
    )
    assert not page.locator("#cloud-warn-backdrop").is_visible()


def test_cloud_warn_session_silence_suppresses_further_prompts(page):
    # Trigger again
    page.locator("#nav-refine").click()
    page.wait_for_timeout(300)
    page.locator("#refine-scene-input").fill("Another scene text.")
    page.locator("#refine-feedback").fill("rendi tense")
    page.locator("#btn-refine").click()
    page.wait_for_function(
        "document.getElementById('cloud-warn-backdrop').classList.contains('visible')",
        timeout=3000,
    )
    # Tick the session-silence checkbox + continue
    page.locator("#cw-skip-session").check()
    page.locator("#cw-btn-continue").click()
    page.wait_for_timeout(2000)
    # Modal closes
    assert not page.locator("#cloud-warn-backdrop").is_visible()
    # Next refine call should NOT prompt
    page.locator("#nav-refine").click()
    page.wait_for_timeout(300)
    page.locator("#refine-scene-input").fill("Third scene text.")
    page.locator("#refine-feedback").fill("change tone")
    page.locator("#btn-refine").click()
    page.wait_for_timeout(2000)
    # Modal MUST NOT be visible after session-silence
    assert not page.locator("#cloud-warn-backdrop").is_visible()


# ── Sprint C2+C3: audit_trail end-to-end ───────────────────────────────────

def test_llm_toggle_triggers_audit_event(page):
    page.locator("#nav-dashboard").click()
    page.wait_for_timeout(400)
    # Switch to verbose to see all events
    page.locator("input[name='activity-mode'][value='verbose']").check()
    page.wait_for_timeout(500)
    # Click toggle (logs llm_routing.switch event server-side)
    page.locator("#dash-btn-uncensored").click()
    page.wait_for_timeout(1500)
    # Force refresh so the feed picks up the just-logged event
    page.locator("#ac-refresh-btn").click()
    page.wait_for_timeout(1500)
    # Verify event landed in feed
    list_html = page.locator("#activity-list").inner_html()
    assert "llm_routing.switch" in list_html
    # Switch back
    page.locator("#dash-btn-uncensored").click()
    page.wait_for_timeout(500)


# ── Sprint A regression ────────────────────────────────────────────────────

def test_privacy_badge_still_works_post_sprint_c(page):
    page.locator("#nav-dashboard").click()
    page.wait_for_timeout(300)
    page.locator("#privacy-badge").hover()
    page.wait_for_timeout(300)
    assert page.locator("#privacy-badge .pb-tooltip").is_visible()
