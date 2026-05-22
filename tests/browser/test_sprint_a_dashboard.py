"""Playwright Python browser-verify for Sprint A Dashboard quick-wins.

Sprint A = vendor CDN + privacy badge + live counters + empty-state helper.
Pytest marker @integration: requires Flask shell running on FLASK_TEST_URL
(default http://127.0.0.1:5002) and playwright + chromium installed.

Run manually:
  (FLASK_APP=app.calliope_shell.server python -m flask run --port 5002 &) && \\
  pytest tests/browser/test_sprint_a_dashboard.py -m integration -v

Skipped if Flask not reachable or playwright unavailable.
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
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        pg = ctx.new_page()
        yield pg
        browser.close()


@pytest.fixture(scope="module")
def loaded_page(page):
    network_log: list[str] = []
    page.on("request", lambda req: network_log.append(req.url))
    page.goto(URL, wait_until="networkidle", timeout=15000)
    page._network_log = network_log
    return page


def test_privacy_badge_present(loaded_page):
    badge = loaded_page.locator("#privacy-badge")
    assert badge.count() == 1
    assert "local-only" in badge.inner_text().lower()


def test_privacy_badge_tooltip_visible_on_hover(loaded_page):
    loaded_page.locator("#privacy-badge").hover()
    loaded_page.wait_for_timeout(300)
    assert loaded_page.locator("#privacy-badge .pb-tooltip").is_visible()


def test_counters_widget_populated(loaded_page):
    loaded_page.wait_for_function(
        "document.getElementById('cnt-chars') && document.getElementById('cnt-chars').textContent !== '…'",
        timeout=10000,
    )
    for cid in ("cnt-chars", "cnt-scenes", "cnt-arcs", "cnt-lore"):
        el = loaded_page.locator(f"#{cid}")
        assert el.count() == 1, f"{cid} missing"
        txt = el.inner_text().strip()
        assert txt and txt != "…", f"{cid} not populated: {txt!r}"


def test_no_external_cdn_requests(loaded_page):
    external = [
        u for u in loaded_page._network_log
        if "cubism.live2d.com" in u or "cdn.jsdelivr.net" in u
    ]
    assert not external, f"external CDN requests detected: {external}"


def test_vendor_scripts_loaded_locally(loaded_page):
    local_vendor = {
        u for u in loaded_page._network_log
        if "/static/js/vendor/" in u
    }
    # Expect 3 local vendor files requested
    assert len(local_vendor) >= 3, f"expected ≥3 vendor requests, got {local_vendor}"


def test_render_empty_state_helper_defined(loaded_page):
    defined = loaded_page.evaluate("typeof window.renderEmptyState === 'function'")
    assert defined, "window.renderEmptyState helper not defined globally"


def test_render_empty_state_renders_into_target(loaded_page):
    # Inject a fresh container, call helper, verify markup
    loaded_page.evaluate("""
        const probe = document.createElement('div');
        probe.id = 'empty-state-probe';
        document.body.appendChild(probe);
        window.renderEmptyState('empty-state-probe', {
            kind: 'empty', icon: '◇', title: 'Probe', hint: 'browser-verify'
        });
    """)
    probe_html = loaded_page.locator("#empty-state-probe").inner_html()
    assert "empty-state" in probe_html
    assert "Probe" in probe_html
    assert "browser-verify" in probe_html
