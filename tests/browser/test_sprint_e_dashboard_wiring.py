"""Playwright Python browser-verify for Sprint E Dashboard wiring.

Sprint E = Smart Draft + Summarize + Lore Check panels + Scene Revive button.
Pytest marker @integration: requires Flask shell running on FLASK_TEST_URL.

Run manually:
  (FLASK_PORT=5002 python -m app.calliope_shell.server &) && \
  pytest tests/browser/test_sprint_e_dashboard_wiring.py -m integration -v
"""
from __future__ import annotations

import os

import pytest

playwright = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

URL = os.environ.get("FLASK_TEST_URL", "http://127.0.0.1:5002/")


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
        reason=f"Flask shell not reachable at {URL} — start manually for browser verify",
    ),
]


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        pg = browser.new_page()
        pg.goto(URL)
        pg.wait_for_load_state("networkidle")
        yield pg
        browser.close()


def test_e1_nav_smartdraft_exists(page):
    nav = page.locator("#nav-smartdraft")
    assert nav.is_visible()
    assert "Smart Draft" in nav.text_content()


def test_e2_nav_summarize_exists(page):
    nav = page.locator("#nav-summarize")
    assert nav.is_visible()
    assert "Summarize" in nav.text_content()


def test_e3_nav_lorecheck_exists(page):
    nav = page.locator("#nav-lorecheck")
    assert nav.is_visible()
    assert "Lore Check" in nav.text_content()


def test_e4_smartdraft_panel_shows(page):
    page.locator("#nav-smartdraft").click()
    panel = page.locator("#smartdraft-panel")
    panel.wait_for(state="visible", timeout=2000)
    assert page.locator("#sd-intent").is_visible()
    assert page.locator("#btn-smartdraft").is_visible()


def test_e5_summarize_panel_shows(page):
    page.locator("#nav-summarize").click()
    panel = page.locator("#summarize-panel")
    panel.wait_for(state="visible", timeout=2000)
    assert page.locator("#sum-text").is_visible()
    assert page.locator("#btn-summarize").is_visible()


def test_e6_lorecheck_panel_shows(page):
    page.locator("#nav-lorecheck").click()
    panel = page.locator("#lorecheck-panel")
    panel.wait_for(state="visible", timeout=2000)
    assert page.locator("#lc-text").is_visible()
    assert page.locator("#btn-lorecheck").is_visible()


def test_e7_smartdraft_validation(page):
    page.locator("#nav-smartdraft").click()
    page.locator("#sd-intent").fill("")
    page.locator("#btn-smartdraft").click()
    status = page.locator("#sd-status")
    assert "intento" in status.text_content().lower() or "intent" in status.text_content().lower()


def test_e8_summarize_validation(page):
    page.locator("#nav-summarize").click()
    page.locator("#sum-text").fill("")
    page.locator("#btn-summarize").click()
    status = page.locator("#sum-status")
    assert "testo" in status.text_content().lower() or "incolla" in status.text_content().lower()


def test_e9_lorecheck_validation(page):
    page.locator("#nav-lorecheck").click()
    page.locator("#lc-text").fill("")
    page.locator("#btn-lorecheck").click()
    status = page.locator("#lc-status")
    assert "testo" in status.text_content().lower() or "inserisci" in status.text_content().lower()
