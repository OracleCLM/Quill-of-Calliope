"""Wave 7 — Smoke clickable browser tests per le 6 view non coperte dal deep review.

Per ogni view: nav click → panel visible → handler con side-effect cliccato →
state assert (loading status mostrato, response renderato, oppure error path
mostrato se backend dependency down — entrambi sono evidence di handler attivo).

LLM gateway / Mascot WS / Discord bot tipicamente DOWN durante test → path
'error path' coperto come graceful degradation evidence.

Run:
  (FLASK_APP=app.calliope_shell.server python -m flask run --port 5004 &) && \\
  pytest tests/browser/test_view_smoke_clickable.py -m integration -v
"""
from __future__ import annotations

import os

import pytest

playwright = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

URL = os.environ.get("FLASK_TEST_URL", "http://127.0.0.1:5004/")


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
        yield pg
        browser.close()


def _nav(page, tab_id: str, panel_id: str):
    page.locator(f"#{tab_id}").click()
    page.wait_for_timeout(400)
    panel = page.locator(f"#{panel_id}")
    assert panel.is_visible(), f"{panel_id} not visible after clicking {tab_id}"
    return panel


# ── Messages view ──────────────────────────────────────────────────────────

class TestMessagesView:
    def test_nav_to_messages_panel(self, page):
        _nav(page, "nav-messages", "messages-panel")

    def test_load_messages_handler_fires(self, page):
        _nav(page, "nav-messages", "messages-panel")
        page.locator("#msg-load-btn").click()
        # Wait for status to populate (either count text OR error)
        page.wait_for_function(
            "document.getElementById('msg-status').textContent.length > 0",
            timeout=8000,
        )
        status = page.locator("#msg-status").inner_text().strip()
        assert status, "msg-status not populated after click"

    def test_messages_char_filter_handler(self, page):
        _nav(page, "nav-messages", "messages-panel")
        page.locator("#msg-char-filter").fill("Aurora")
        page.locator("#msg-load-btn").click()
        page.wait_for_timeout(2000)
        status = page.locator("#msg-status").inner_text()
        assert "Aurora" in status or "0" in status or "messag" in status.lower()


# ── Scenes view ────────────────────────────────────────────────────────────

class TestScenesView:
    def test_nav_to_scenes_panel(self, page):
        _nav(page, "nav-scenes", "scenes-panel")

    def test_scenes_list_loads(self, page):
        _nav(page, "nav-scenes", "scenes-panel")
        page.wait_for_function(
            "document.getElementById('scenes-list').children.length > 0 && "
            "!document.getElementById('scenes-list').textContent.includes('Caricamento')",
            timeout=10000,
        )
        # List should have at least one item (or empty-state markup)
        ul = page.locator("#scenes-list")
        assert ul.locator("li, .empty-state").count() > 0

    def test_scenes_filter_handler(self, page):
        _nav(page, "nav-scenes", "scenes-panel")
        page.wait_for_function(
            "document.getElementById('scenes-list').children.length > 0",
            timeout=10000,
        )
        page.locator("#scene-filter").fill("xyzzy-nonexistent-filter")
        page.wait_for_timeout(300)
        # Empty-state should kick in via _renderSceneList
        empty = page.locator("#scenes-list .empty-state")
        assert empty.count() > 0 or page.locator("#scenes-list li").count() == 0

    def test_scene_detail_loads_on_click(self, page):
        _nav(page, "nav-scenes", "scenes-panel")
        page.locator("#scene-filter").fill("")
        page.wait_for_timeout(300)
        first = page.locator("#scenes-list li").first
        if first.count() == 0:
            pytest.skip("no scenes in DB to click")
        first.click()
        page.wait_for_function(
            "document.getElementById('scene-detail').style.display !== 'none'",
            timeout=5000,
        )
        title = page.locator("#scene-detail-title").inner_text().strip()
        assert title and title != "…"


# ── Translate view ─────────────────────────────────────────────────────────

class TestTranslateView:
    def test_nav_to_translate_panel(self, page):
        _nav(page, "nav-translate", "translate-panel")

    def test_translate_handler_fires_with_error_path(self, page):
        """LLM gateway DOWN → handler still fires + status.error rendered."""
        _nav(page, "nav-translate", "translate-panel")
        page.locator("#translate-input").fill("ciao mondo")
        # btn-translate is registered via /static/js/translate.js
        page.locator("#btn-translate").click()
        page.wait_for_function(
            "document.getElementById('translate-status').textContent.length > 0",
            timeout=10000,
        )
        status = page.locator("#translate-status").inner_text()
        assert status, "translate-status empty after click"


# ── Draft view ─────────────────────────────────────────────────────────────

class TestDraftView:
    def test_nav_to_draft_panel(self, page):
        _nav(page, "nav-draft", "draft-panel")

    def test_draft_generate_handler_fires(self, page):
        """LLM gateway likely DOWN → handler renders error path in status."""
        _nav(page, "nav-draft", "draft-panel")
        page.locator("#draft-prompt").fill("Aurora draws her sword")
        page.locator("#btn-draft-generate").click()
        # Wait until status changes from idle (gen takes time even on error)
        page.wait_for_function(
            "document.getElementById('draft-status').textContent.length > 0",
            timeout=20000,
        )
        status = page.locator("#draft-status").inner_text()
        assert status

    def test_draft_empty_prompt_validation(self, page):
        _nav(page, "nav-draft", "draft-panel")
        page.locator("#draft-prompt").fill("")
        page.locator("#btn-draft-generate").click()
        page.wait_for_timeout(500)
        status = page.locator("#draft-status").inner_text()
        assert "prompt" in status.lower() or "inserisci" in status.lower()


# ── Refine view ────────────────────────────────────────────────────────────

class TestRefineView:
    def test_nav_to_refine_panel(self, page):
        _nav(page, "nav-refine", "refine-panel")

    def test_refine_handler_validation_empty_scene(self, page):
        _nav(page, "nav-refine", "refine-panel")
        page.locator("#refine-scene-input").fill("")
        page.locator("#refine-feedback").fill("test")
        page.locator("#btn-refine").click()
        page.wait_for_timeout(500)
        status = page.locator("#refine-status").inner_text()
        assert "scena" in status.lower() or "scene" in status.lower() or "incolla" in status.lower()

    def test_refine_handler_validation_empty_feedback(self, page):
        _nav(page, "nav-refine", "refine-panel")
        page.locator("#refine-scene-input").fill("Original scene text here.")
        page.locator("#refine-feedback").fill("")
        page.locator("#btn-refine").click()
        page.wait_for_timeout(500)
        status = page.locator("#refine-status").inner_text()
        assert "feedback" in status.lower() or "inserisci" in status.lower()

    def test_refine_handler_fires_on_valid_input(self, page):
        _nav(page, "nav-refine", "refine-panel")
        page.locator("#refine-scene-input").fill("Original scene text here.")
        page.locator("#refine-feedback").fill("accorcia e rendi più tense")
        page.locator("#btn-refine").click()
        page.wait_for_function(
            "document.getElementById('refine-status').textContent.length > 0",
            timeout=15000,
        )
        status = page.locator("#refine-status").inner_text()
        # Either success or error — both indicate handler fired
        assert status


# ── Arc view ───────────────────────────────────────────────────────────────

class TestArcView:
    def test_nav_to_arc_panel(self, page):
        _nav(page, "nav-arc", "arc-panel")

    def test_arc_list_loads(self, page):
        _nav(page, "nav-arc", "arc-panel")
        page.wait_for_function(
            "document.getElementById('arc-ul').children.length > 0 && "
            "!document.getElementById('arc-ul').textContent.includes('Caricamento')",
            timeout=10000,
        )

    def test_arc_detail_loads_on_click(self, page):
        _nav(page, "nav-arc", "arc-panel")
        first = page.locator("#arc-ul li").first
        if first.count() == 0:
            pytest.skip("no arcs in DB")
        first.click()
        page.wait_for_function(
            "document.getElementById('arc-detail-content').style.display === 'block'",
            timeout=5000,
        )
        title = page.locator("#arc-detail-title").inner_text().strip()
        assert title

    def test_arc_regenerate_summary_handler(self, page):
        _nav(page, "nav-arc", "arc-panel")
        first = page.locator("#arc-ul li").first
        if first.count() == 0:
            pytest.skip("no arcs in DB")
        first.click()
        page.wait_for_timeout(500)
        page.locator("#arc-btn-summary").click()
        # Status changes to "Generating..." then settles
        page.wait_for_function(
            "document.getElementById('arc-status').textContent.length === 0 || "
            "document.getElementById('arc-summary-box').style.display === 'block'",
            timeout=15000,
        )

    def test_arc_detect_threads_handler(self, page):
        _nav(page, "nav-arc", "arc-panel")
        first = page.locator("#arc-ul li").first
        if first.count() == 0:
            pytest.skip("no arcs in DB")
        first.click()
        page.wait_for_timeout(500)
        page.locator("#arc-btn-threads").click()
        page.wait_for_function(
            "document.getElementById('arc-threads-list').innerHTML.length > 0",
            timeout=10000,
        )

    def test_arc_continue_handler(self, page):
        _nav(page, "nav-arc", "arc-panel")
        first = page.locator("#arc-ul li").first
        if first.count() == 0:
            pytest.skip("no arcs in DB")
        first.click()
        page.wait_for_timeout(500)
        page.locator("#arc-hint-input").fill("test hint")
        page.locator("#arc-btn-continue").click()
        # Either result renders OR status shows error
        page.wait_for_function(
            "document.getElementById('arc-continue-result').style.display === 'block' || "
            "document.getElementById('arc-status').textContent.length > 0",
            timeout=15000,
        )


# ── Home view (Sprint A regression) ────────────────────────────────────────

class TestHomeView:
    def test_nav_to_home_main_view(self, page):
        page.locator("#nav-home").click()
        page.wait_for_timeout(400)
        assert page.locator("#main-view").is_visible()

    def test_char_list_loaded_in_sidebar(self, page):
        page.locator("#nav-home").click()
        page.wait_for_timeout(500)
        page.wait_for_function(
            "document.getElementById('char-list').children.length > 0 && "
            "!document.getElementById('char-list').textContent.includes('Caricamento')",
            timeout=10000,
        )
        # At least one char li
        chars = page.locator("#char-list li")
        assert chars.count() >= 1

    def test_char_click_loads_memory_panel(self, page):
        page.locator("#nav-home").click()
        page.wait_for_timeout(500)
        first = page.locator("#char-list li").first
        if first.count() == 0:
            pytest.skip("no chars in DB")
        first.click()
        page.wait_for_function(
            "document.getElementById('char-memory-details').style.display === 'block'",
            timeout=5000,
        )
