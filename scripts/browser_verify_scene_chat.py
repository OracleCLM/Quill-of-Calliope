"""C1 browser-verify: thread-chat + compose narratore/personaggio (Playwright-Python).

Seed DB temporaneo (NESSUN tocco ai dati reali) -> Flask -> Playwright:
  1. apre la vista scene, carica la lista, clicca la scena seedata
  2. verifica che il thread renderizzi le bolle (>=2 messaggi seedati)
  3. scrive come Narratore e invia -> verifica che compaia la nuova bolla
"""
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = "5099"
SID = "scene-c1-verify"

sys.path.insert(0, REPO)
from app.db import get_db, init_schema, new_id  # noqa: E402
from app.db.characters import add_character_to_scene  # noqa: E402
from app.db.messages import add_message  # noqa: E402

tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name


def seed():
    conn = get_db(tmp_db)
    init_schema(conn)
    conn.execute(
        "INSERT INTO scenes(id,title,created_at,updated_at) "
        "VALUES(?,?,datetime('now'),datetime('now'))",
        (SID, "C1 Verify Scene"),
    )
    cid = new_id()
    conn.execute(
        "INSERT INTO characters(id,name,created_at,updated_at) "
        "VALUES(?,?,datetime('now'),datetime('now'))",
        (cid, "Aria"),
    )
    conn.commit()
    add_character_to_scene(conn, SID, cid, role="protagonist")
    # Narratore (nessun character_id) + personaggio.
    add_message(conn, scene_id=SID, author_name="Narratore",
                content_original="The great hall falls silent.", position_order=0)
    add_message(conn, scene_id=SID, character_id=cid, author_name="Aria",
                content_original="I draw my blade.", position_order=1)
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
    env = dict(os.environ, CALLIOPE_DB_PATH=tmp_db, FLASK_PORT=PORT)
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
            # Vista scene + carica lista.
            page.evaluate("showView('scenes')")
            page.evaluate("_loadScenes()")
            page.wait_for_selector("#scenes-list li", timeout=8000)
            # Clicca la scena seedata (path di click reale).
            page.click("#scenes-list li:has-text('C1 Verify Scene')")
            page.wait_for_selector("#scene-thread .msg-bubble", timeout=8000)
            n0 = page.locator("#scene-thread .msg-bubble").count()
            print(f"CHECK thread bubbles iniziali: {n0}")
            assert n0 >= 2, f"attese >=2 bolle, trovate {n0}"
            # Verifica stile narratore presente.
            n_narr = page.locator("#scene-thread .msg-bubble.msg-narrator").count()
            print(f"CHECK bolle narratore: {n_narr}")
            assert n_narr >= 1, "attesa >=1 bolla narratore"
            # Verifica testo seedato presente.
            assert page.locator("text=The great hall falls silent.").count() >= 1
            assert page.locator("text=I draw my blade.").count() >= 1
            # Compose come Narratore (default) e invia.
            page.fill("#scene-compose-text", "A cold wind sweeps through.")
            page.click("#scene-send-btn")
            page.wait_for_function(
                "document.querySelectorAll('#scene-thread .msg-bubble').length >= 3",
                timeout=8000,
            )
            n1 = page.locator("#scene-thread .msg-bubble").count()
            print(f"CHECK thread bubbles dopo invio: {n1}")
            assert n1 == n0 + 1, f"atteso {n0+1}, trovate {n1}"
            assert page.locator("text=A cold wind sweeps through.").count() >= 1
            print("CHECK nuovo messaggio narratore presente nel thread: OK")
            browser.close()
        print("BROWSER-VERIFY C1: PASS")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        os.unlink(tmp_db)


if __name__ == "__main__":
    sys.exit(main())
