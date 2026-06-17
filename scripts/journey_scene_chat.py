"""Journey-test scene-chat (Playwright-Python) — VERIFICA A STATO-RISULTANTE.

Nuovo standard (non assert-presenza): guida l'app come un utente vero e verifica lo
STATO finale di ogni flusso reale, inclusa la PERSISTENZA dopo reload. I journey sono
scritti Given-When-Then. Eseguibile standalone (Flask con DB temp seedato + stub-gateway):

    python scripts/journey_scene_chat.py

Exit 0 = tutti i journey PASS. Da rilanciare a inizio-sessione come regressione UI.
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
PORT = "5079"
GW_PORT = 8779
SID = "scene-journey"

sys.path.insert(0, REPO)
from app.db import get_db, init_schema, new_id  # noqa: E402
from app.db.characters import add_character_to_scene  # noqa: E402
from app.db.messages import add_message  # noqa: E402

tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
_FAILS = []


class _GwHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n)
        prompt = ""
        try:
            prompt = json.loads(raw or b"{}").get("prompt", "")
        except ValueError:
            pass
        # Adversarial: se il messaggio contiene FORCE503 il gateway è "sovraccarico".
        if "FORCE503" in prompt:
            body = json.dumps({"code": "queue_exceeded", "type": "too_many_requests_error"}).encode()
            status = 503
        else:
            body = json.dumps({"content": "[REFINED] Una prosa raffinata."}).encode()
            status = 200
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def seed():
    """Scena con position_order NON-contigui (come i dati Discord importati)."""
    conn = get_db(tmp_db)
    init_schema(conn)
    conn.execute(
        "INSERT INTO scenes(id,title,created_at,updated_at) "
        "VALUES(?,?,datetime('now'),datetime('now'))", (SID, "Journey Scene"))
    cid = new_id()
    conn.execute(
        "INSERT INTO characters(id,name,card_json,created_at,updated_at) "
        "VALUES(?,?,?,datetime('now'),datetime('now'))",
        (cid, "Aria", json.dumps({"traits": ["brave"]})))
    conn.commit()
    add_character_to_scene(conn, SID, cid, role="protagonist")
    for pos, txt in [(66, "Primo turno importato"), (67, "Secondo"), (16541, "Ultimo importato")]:
        add_message(conn, scene_id=SID, character_id=cid, author_name="Aria",
                    content_original=txt, position_order=pos)
    # Messaggio che forza il 503 del gateway (caso adversarial).
    add_message(conn, scene_id=SID, character_id=cid, author_name="Aria",
                content_original="FORCE503 testo da raffinare", position_order=16542)
    conn.commit()
    conn.close()


def wait_health():
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=1) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def _open_scene(pg):
    pg.goto(f"http://127.0.0.1:{PORT}/", wait_until="domcontentloaded")
    pg.evaluate("showView('scenes')")
    pg.wait_for_selector("#scenes-list li", timeout=10000)
    pg.click("#scenes-list li:has-text('Journey Scene')")
    pg.wait_for_selector("#scene-thread .msg-bubble", timeout=10000)


def journey_message_appends_at_tail(pg):
    """Given scena-attiva con position sparse, When invio un turno come Narratore,
    Then compare come ULTIMA bolla del thread E persiste dopo reload."""
    name = "MSG-APPENDS-AT-TAIL"
    _open_scene(pg)
    marker = "TURNO_NUOVO_IN_CODA_777"
    pg.fill("#scene-compose-text", marker)
    pg.click("#scene-send-btn")
    # When: attendi che l'ultima bolla contenga il marker (auto-retry, no sleep fisso).
    try:
        pg.wait_for_function(
            """(m) => {
                const bs = document.querySelectorAll('#scene-thread .msg-bubble');
                if (!bs.length) return false;
                const last = bs[bs.length - 1];
                return last.querySelector('.msg-text') &&
                       last.querySelector('.msg-text').textContent.includes(m);
            }""",
            arg=marker, timeout=10000,
        )
    except Exception:
        _FAILS.append(f"{name}: il nuovo turno NON è l'ultima bolla dopo l'invio")
        return
    # Then-persistenza: reload + riapri -> il turno è ANCORA l'ultima bolla.
    _open_scene(pg)
    try:
        pg.wait_for_function(
            """(m) => {
                const bs = document.querySelectorAll('#scene-thread .msg-bubble');
                if (!bs.length) return false;
                const last = bs[bs.length - 1];
                return last.querySelector('.msg-text') &&
                       last.querySelector('.msg-text').textContent.includes(m);
            }""",
            arg=marker, timeout=10000,
        )
        print(f"[PASS] {name}")
    except Exception:
        _FAILS.append(f"{name}: il turno NON persiste come ultima bolla dopo reload")


def journey_refine(pg):
    """Given un messaggio, When clicco 'raffina', Then vedo il testo raffinato nel pannello."""
    name = "REFINE-RENDER"
    _open_scene(pg)
    pg.click("#scene-thread .msg-bubble .msg-refine-btn")
    try:
        pg.wait_for_function(
            """() => {
                const t = document.querySelector('#scene-thread .msg-refined-text');
                return t && t.textContent.includes('REFINED');
            }""",
            timeout=10000,
        )
        print(f"[PASS] {name}")
    except Exception:
        _FAILS.append(f"{name}: pannello raffinato non mostra il testo atteso")


def journey_refine_503_clean(pg):
    """Given gateway sovraccarico (503), When clicco 'raffina', Then vedo un MESSAGGIO
    PULITO + bottone Riprova, NON il pannello raffinato né un DOM rotto."""
    name = "REFINE-503-CLEAN"
    _open_scene(pg)
    pg.locator("#scene-thread .msg-bubble:has-text('FORCE503') .msg-refine-btn").click()
    try:
        pg.wait_for_function(
            """() => {
                const e = document.querySelector('#scene-thread .msg-bubble .msg-refined-error');
                return e && e.querySelector('.msg-refine-retry');
            }""",
            timeout=20000,
        )
    except Exception:
        _FAILS.append(f"{name}: nessun messaggio-errore pulito + Riprova mostrato")
        return
    refined = pg.locator(
        "#scene-thread .msg-bubble:has-text('FORCE503') .msg-refined-text").count()
    if refined:
        _FAILS.append(f"{name}: mostrato testo raffinato nonostante il 503")
        return
    print(f"[PASS] {name}")


def main():
    seed()
    gw = HTTPServer(("127.0.0.1", GW_PORT), _GwHandler)
    threading.Thread(target=gw.serve_forever, daemon=True).start()
    env = dict(os.environ, CALLIOPE_DB_PATH=tmp_db, FLASK_PORT=PORT,
               GATEWAY_URL=f"http://127.0.0.1:{GW_PORT}", CALLIOPE_WRITE_FALLBACKS="")
    proc = subprocess.Popen([sys.executable, "-m", "app.calliope_shell.server"],
                            cwd=REPO, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not wait_health():
            print("FAIL: Flask down")
            return 1
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            br = p.chromium.launch()
            pg = br.new_page()
            journey_message_appends_at_tail(pg)
            journey_refine(pg)
            journey_refine_503_clean(pg)
            br.close()
        if _FAILS:
            print("\n===== JOURNEY FAILURES =====")
            for f in _FAILS:
                print("  [FAIL]", f)
            return 1
        print("\nJOURNEY scene-chat: ALL PASS")
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
