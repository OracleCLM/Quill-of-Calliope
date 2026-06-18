"""Browser-verify M-D — pannello-azioni CONTESTUALE su testo selezionato.

VERIFICA A STATO-RISULTANTE (Given-When-Then), guidando l'app come un utente:
  J1  Given testo nel compositore, When seleziono una porzione, Then COMPARE un
      SOLO pannello con i 6 verbi (UI unica, non 6 bottoni sparsi).  [screenshot 1]
  J2  Given il pannello aperto, When clicco 'Traduci' (→ /api/write reale) e poi
      'Sostituisci', Then il testo selezionato nel compositore è SOSTITUITO dal
      risultato.  [screenshot 2]
  J3  Given una selezione in una BOLLA del thread (read-only), When agisco e
      applico, Then il risultato è INSERITO nel compositore (non perso).

Gateway: usa quello REALE (localhost:8766) per un end-to-end vero su 'traduci'
(groq). Lanciabile standalone:  python scripts/journey_write_actions_panel.py
Exit 0 = tutti i journey PASS. Salva 2 screenshot in RESULTS/.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = "5081"
SID = "scene-md"
GATEWAY = os.environ.get("MD_GATEWAY_URL", "http://localhost:8766")

sys.path.insert(0, REPO)
from app.db import get_db, init_schema, new_id  # noqa: E402
from app.db.characters import add_character_to_scene  # noqa: E402
from app.db.messages import add_message  # noqa: E402

tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
RESULTS = os.path.join(REPO, "RESULTS")
os.makedirs(RESULTS, exist_ok=True)
_FAILS = []


def seed():
    conn = get_db(tmp_db)
    init_schema(conn)
    conn.execute(
        "INSERT INTO scenes(id,title,created_at,updated_at) "
        "VALUES(?,?,datetime('now'),datetime('now'))", (SID, "Scena M-D"))
    cid = new_id()
    conn.execute(
        "INSERT INTO characters(id,name,card_json,created_at,updated_at) "
        "VALUES(?,?,?,datetime('now'),datetime('now'))",
        (cid, "Aria", json.dumps({"traits": ["brave"]})))
    conn.commit()
    add_character_to_scene(conn, SID, cid, role="protagonist")
    add_message(conn, scene_id=SID, character_id=cid, author_name="Aria",
                content_original="The dragon sleeps in the ancient cavern.",
                position_order=0)
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
    pg.evaluate(f"_loadSceneDetail('{SID}')")
    pg.wait_for_selector("#scene-thread .msg-bubble", timeout=10000)
    # Silenzia l'avviso-cloud per un flusso deterministico (l'operatore può farlo via UI).
    pg.evaluate("window._cloudWarnSessionSilenced = true")


def _select_in_textarea(pg, text, start, end):
    pg.fill("#scene-compose-text", text)
    pg.evaluate(
        """([s,e]) => {
            const ta = document.getElementById('scene-compose-text');
            ta.focus();
            ta.setSelectionRange(s, e);
            const r = ta.getBoundingClientRect();
            ta.dispatchEvent(new MouseEvent('mouseup', {bubbles:true,
                clientX:r.left+20, clientY:r.top+12, view:window}));
        }""", [start, end])


def journey_panel_appears(pg):
    """J1: selezione nel compositore → UN pannello con i 6 verbi."""
    name = "MD-PANEL-APPEARS"
    _open_scene(pg)
    _select_in_textarea(pg, "Il drago dorme nella caverna antica.", 0, 10)
    try:
        pg.wait_for_selector(".write-actions-pop", state="visible", timeout=6000)
        n_pop = pg.evaluate("document.querySelectorAll('.write-actions-pop').length")
        n_btn = pg.evaluate("document.querySelectorAll('.write-actions-pop .wa-btn').length")
        if n_pop != 1:
            _FAILS.append(f"{name}: attesi 1 pannello, trovati {n_pop} (UI non-unica)")
            return
        if n_btn != 6:
            _FAILS.append(f"{name}: attesi 6 verbi nel pannello, trovati {n_btn}")
            return
        pg.screenshot(path=os.path.join(RESULTS, "md_panel_appears.png"))
        print(f"[PASS] {name} (1 pannello, 6 verbi)")
    except Exception as e:
        _FAILS.append(f"{name}: pannello non comparso su selezione ({e})")


def journey_translate_replaces(pg):
    """J2: 'Traduci' → /api/write reale → 'Sostituisci' rimpiazza la selezione."""
    name = "MD-TRANSLATE-REPLACES"
    _open_scene(pg)
    src = "Il guerriero impugna la spada e avanza nella nebbia."
    _select_in_textarea(pg, src, 0, len(src))  # seleziona tutto
    try:
        pg.wait_for_selector(".write-actions-pop", state="visible", timeout=6000)
        pg.click(".write-actions-pop .wa-btn:has-text('Traduci')")
        # /api/write reale (groq) → preview con Applica.
        pg.wait_for_selector(".write-actions-pop .wa-preview", timeout=40000)
        preview = pg.evaluate(
            "(document.querySelector('.wa-preview')||{}).textContent || ''")
        if not preview.strip():
            _FAILS.append(f"{name}: preview vuota dopo traduci")
            return
        pg.screenshot(path=os.path.join(RESULTS, "md_translate_result.png"))
        pg.click(".write-actions-pop .wa-apply")
        # STATO-RISULTANTE: il compositore NON contiene più l'originale italiano,
        # ma il testo tradotto (== preview applicata).
        pg.wait_for_function(
            "(o)=>{const v=document.getElementById('scene-compose-text').value;"
            "return v && v !== o && v.trim().length>0;}", arg=src, timeout=6000)
        applied = pg.evaluate("document.getElementById('scene-compose-text').value")
        if applied.strip() == preview.strip():
            print(f"[PASS] {name} (selezione sostituita col risultato /api/write)")
        else:
            _FAILS.append(f"{name}: testo applicato != risultato (got {applied[:60]!r})")
    except Exception as e:
        _FAILS.append(f"{name}: flusso traduci→applica fallito ({e})")


def journey_bubble_inserts(pg):
    """J3: selezione in una bolla read-only → 'Inserisci nel compositore'."""
    name = "MD-BUBBLE-INSERTS"
    _open_scene(pg)
    pg.evaluate("document.getElementById('scene-compose-text').value=''")
    # Seleziona il testo della prima bolla del thread.
    pg.evaluate(
        """() => {
            const el = document.querySelector('#scene-thread .msg-bubble .msg-text');
            const r = document.createRange(); r.selectNodeContents(el);
            const s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
            const bb = el.getBoundingClientRect();
            document.dispatchEvent(new MouseEvent('mouseup', {bubbles:true,
                clientX:bb.left+10, clientY:bb.top+8, view:window}));
        }""")
    try:
        pg.wait_for_selector(".write-actions-pop", state="visible", timeout=6000)
        # 'Traduci' è veloce/economico; verifica che l'apply INSERISCA nel compositore.
        pg.click(".write-actions-pop .wa-btn:has-text('Traduci')")
        pg.wait_for_selector(".write-actions-pop .wa-preview", timeout=40000)
        # da bolla read-only il bottone è 'Inserisci nel compositore'.
        label = pg.evaluate("(document.querySelector('.wa-apply')||{}).textContent||''")
        if "compositore" not in label.lower():
            _FAILS.append(f"{name}: da bolla il bottone non è 'Inserisci nel compositore' ({label!r})")
            return
        pg.click(".write-actions-pop .wa-apply")
        pg.wait_for_function(
            "()=>{const v=document.getElementById('scene-compose-text').value;"
            "return v && v.trim().length>0;}", timeout=6000)
        print(f"[PASS] {name} (risultato inserito nel compositore da bolla read-only)")
    except Exception as e:
        _FAILS.append(f"{name}: flusso bolla→inserisci fallito ({e})")


def main():
    seed()
    env = dict(os.environ, CALLIOPE_DB_PATH=tmp_db, FLASK_PORT=PORT,
               GATEWAY_URL=GATEWAY, CALLIOPE_EMBED_ST="0")
    proc = subprocess.Popen([sys.executable, "-m", "app.calliope_shell.server"],
                            cwd=REPO, env=env, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    try:
        if not wait_health():
            print("FAIL: Flask down")
            return 1
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            br = p.chromium.launch()
            pg = br.new_page(viewport={"width": 1280, "height": 900})
            journey_panel_appears(pg)
            journey_translate_replaces(pg)
            journey_bubble_inserts(pg)
            br.close()
        if _FAILS:
            print("\n===== M-D FAILURES =====")
            for f in _FAILS:
                print("  [FAIL]", f)
            return 1
        print("\nJOURNEY write-actions-panel (M-D): ALL PASS")
        print("screenshot:", os.path.join(RESULTS, "md_panel_appears.png"))
        print("screenshot:", os.path.join(RESULTS, "md_translate_result.png"))
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
