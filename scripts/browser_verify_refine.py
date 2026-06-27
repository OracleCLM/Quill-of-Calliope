"""R2 browser-verify: pulsante "raffina" end-to-end (Playwright-Python).

Stub-gateway locale (ritorna testo raffinato) + DB temp seedato -> Flask -> Playwright:
  1. apre la scena, clicca il pulsante "✦ raffina" sul messaggio
  2. verifica che il pannello raffinato compaia col testo dello stub-gateway
  3. clicca il toggle "vedi originale" e verifica lo swap
Nessuna chiamata LLM reale: il gateway è uno stub HTTP locale.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = "5099"
GW_PORT = 8799
SID = "scene-r2-verify"
REFINED = "[REFINED] The hall blazed with sudden light."

sys.path.insert(0, REPO)
from app.db import get_db, init_schema, new_id  # noqa: E402
from app.db.characters import add_character_to_scene  # noqa: E402
from app.db.messages import add_message  # noqa: E402

tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name


class _GwHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        body = json.dumps({"content": REFINED}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def seed():
    conn = get_db(tmp_db)
    init_schema(conn)
    conn.execute(
        "INSERT INTO scenes(id,title,created_at,updated_at) "
        "VALUES(?,?,datetime('now'),datetime('now'))",
        (SID, "R2 Verify Scene"),
    )
    cid = new_id()
    conn.execute(
        "INSERT INTO characters(id,name,created_at,updated_at) "
        "VALUES(?,?,datetime('now'),datetime('now'))",
        (cid, "Aria"),
    )
    conn.commit()
    add_character_to_scene(conn, SID, cid, role="protagonist")
    add_message(conn, scene_id=SID, character_id=cid, author_name="Aria",
                content_original="The hall is dark.", position_order=0)
    conn.commit()
    conn.close()


def wait_health():
    for _ in range(50):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=1) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def main():
    seed()
    gw = HTTPServer(("127.0.0.1", GW_PORT), _GwHandler)
    threading.Thread(target=gw.serve_forever, daemon=True).start()

    env = dict(os.environ, CALLIOPE_DB_PATH=tmp_db, FLASK_PORT=PORT,
               GATEWAY_URL=f"http://127.0.0.1:{GW_PORT}")
    proc = subprocess.Popen(
        [sys.executable, "-m", "app.calliope_shell.server"],
        cwd=REPO, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        if not wait_health():
            print("FAIL: Flask non risponde su /health")
            return 1
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"http://127.0.0.1:{PORT}/", wait_until="domcontentloaded")
            page.evaluate("showView('scenes')")
            page.evaluate("_loadScenes()")
            page.wait_for_selector("#scenes-list li", timeout=8000)
            page.click("#scenes-list li:has-text('R2 Verify Scene')")
            page.wait_for_selector("#scene-thread .msg-bubble", timeout=8000)
            # Clic reale sul pulsante raffina del primo messaggio.
            page.click("#scene-thread .msg-bubble .msg-refine-btn")
            page.wait_for_selector("#scene-thread .msg-refined .msg-refined-text", timeout=8000)
            refined = page.locator("#scene-thread .msg-refined-text").first.inner_text()
            print(f"CHECK pannello raffinato: {refined!r}")
            assert REFINED in refined, f"atteso testo stub-gateway, trovato {refined!r}"
            # Toggle -> vedi originale.
            page.click("#scene-thread .msg-refined-label a")
            page.wait_for_function(
                "document.querySelector('#scene-thread .msg-refined-text').textContent.includes('The hall is dark.')",
                timeout=5000,
            )
            orig = page.locator("#scene-thread .msg-refined-text").first.inner_text()
            print(f"CHECK toggle originale: {orig!r}")
            assert "The hall is dark." in orig
            # Tag "raffinato" presente.
            assert page.locator("#scene-thread .msg-refine-btn:has-text('raffinato')").count() >= 1
            browser.close()
        print("BROWSER-VERIFY R2: PASS")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        gw.shutdown()
        os.unlink(tmp_db)


if __name__ == "__main__":
    sys.exit(main())
