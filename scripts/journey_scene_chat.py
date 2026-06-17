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
SID_EMPTY = "scene-journey-empty"
SID_SHEET = "scene-journey-sheet"

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
            # Echo del prompt ricevuto: permette al journey di VERIFICARE cosa è stato
            # iniettato (schede-attive + lore) nel prompt inviato al gateway (GAP-3).
            body = json.dumps({"content": "[REFINED]\n" + prompt[:2000]}).encode()
            status = 200
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def seed(chars_dir):
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
    # Per il journey-binding: una scena VUOTA (roster vuoto) + un char DB NON bindato.
    conn.execute(
        "INSERT INTO scenes(id,title,created_at,updated_at) "
        "VALUES(?,?,datetime('now'),datetime('now'))", (SID_EMPTY, "Scena Senza Roster"))
    bid = new_id()
    conn.execute(
        "INSERT INTO characters(id,name,created_at,updated_at) "
        "VALUES(?,?,datetime('now'),datetime('now'))", (bid, "Bruno Test"))
    # GAP-3: scena con un char (card_json VUOTO) la cui scheda RICCA è in YAML ->
    # il refine deve iniettare la scheda ricca (backstory) nel prompt, non name-only.
    conn.execute(
        "INSERT INTO scenes(id,title,created_at,updated_at) "
        "VALUES(?,?,datetime('now'),datetime('now'))", (SID_SHEET, "Scena Scheda Ricca"))
    gid = new_id()
    conn.execute(
        "INSERT INTO characters(id,name,created_at,updated_at) "
        "VALUES(?,?,datetime('now'),datetime('now'))", (gid, "Galad"))
    conn.commit()
    add_character_to_scene(conn, SID_SHEET, gid, role="protagonist")
    add_message(conn, scene_id=SID_SHEET, character_id=gid, author_name="Galad",
                content_original="Galad avanza nella sala.", position_order=0)
    conn.commit()
    conn.close()
    # Scheda RICCA in YAML (fonte canonica) per Galad.
    with open(os.path.join(chars_dir, "galad.draft.yaml"), "w", encoding="utf-8") as f:
        f.write("name: Galad\nbackstory: Cresciuto tra i ghiacci del nord glaciale.\n"
                "personality: stoico, leale\n")


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


def journey_home_landing(pg):
    """Given apro la Home, Then vedo card d'ingresso chiare e NESSUN errore SillyTavern."""
    name = "HOME-LANDING-AFFORDANCE"
    pg.goto(f"http://127.0.0.1:{PORT}/", wait_until="domcontentloaded")
    pg.evaluate("showView('home')")
    try:
        pg.wait_for_function(
            """() => {
                const v = document.getElementById('main-view');
                if (!v) return false;
                const t = v.innerText || '';
                return t.includes('Apri Scene-Chat') && t.includes('Nuova scena')
                    && t.includes('Nuovo personaggio') && !t.includes('non raggiungibile');
            }""",
            timeout=8000,
        )
        print(f"[PASS] {name}")
    except Exception:
        _FAILS.append(f"{name}: Home non mostra le card d'ingresso o mostra ancora l'errore SillyTavern")


def journey_create_scene(pg):
    """Given clic 'Nuova scena' con un titolo, Then la scena nuova si apre col suo titolo."""
    name = "CREATE-SCENE"
    title = "Scena Journey Nuova"
    pg.goto(f"http://127.0.0.1:{PORT}/", wait_until="domcontentloaded")
    pg.evaluate("showView('scenes')")
    pg.wait_for_selector("#scene-new-btn", timeout=8000)
    pg.once("dialog", lambda d: d.accept(title))
    pg.click("#scene-new-btn")
    try:
        pg.wait_for_function(
            "(t) => (document.getElementById('scene-detail-title')||{}).textContent === t",
            arg=title, timeout=8000,
        )
        print(f"[PASS] {name}")
    except Exception:
        _FAILS.append(f"{name}: la scena creata non si è aperta col titolo atteso")


def journey_create_character(pg):
    """Given clic 'Nuovo personaggio' con un nome, Then compare nella griglia personaggi."""
    name = "CREATE-CHARACTER"
    cname = "Pers Journey XYZ"

    def _h(d):
        d.accept(cname) if d.type == "prompt" else d.accept()

    pg.goto(f"http://127.0.0.1:{PORT}/", wait_until="domcontentloaded")
    pg.evaluate("showView('characters')")
    pg.wait_for_selector("#char-new-btn", timeout=8000)
    pg.on("dialog", _h)
    pg.click("#char-new-btn")
    try:
        pg.wait_for_function(
            "(n) => (document.getElementById('characters-grid')||{}).innerText.includes(n)",
            arg=cname, timeout=8000,
        )
        print(f"[PASS] {name}")
    except Exception:
        _FAILS.append(f"{name}: il personaggio creato non compare nella griglia")
    finally:
        pg.remove_listener("dialog", _h)


def journey_binding_write_as_character(pg):
    """Given una scena SENZA roster + un char DB, When lo aggiungo e scrivo come lui,
    Then il char compare come chip + opzione-compose E il turno è attribuito a LUI."""
    name = "BINDING-WRITE-AS-CHARACTER"
    pg.goto(f"http://127.0.0.1:{PORT}/", wait_until="domcontentloaded")
    pg.evaluate("showView('scenes')")
    pg.evaluate(f"_loadSceneDetail('{SID_EMPTY}')")
    try:
        pg.wait_for_selector("#roster-add-select", timeout=8000)
        # roster inizialmente vuoto
        n_opt = pg.evaluate("document.getElementById('roster-add-select').length")
        if n_opt <= 1:
            _FAILS.append(f"{name}: nessun char DB selezionabile (route /api/db/characters?)")
            return
        val = pg.evaluate("document.getElementById('roster-add-select').options[1].value")
        cname = pg.evaluate("document.getElementById('roster-add-select').options[1].text")
        pg.evaluate(f"_addCharToScene('{val}')")
        pg.wait_for_function(
            "(n)=>{const c=document.querySelectorAll('#scene-roster-chips .roster-chip');"
            "return [...c].some(x=>x.textContent.includes(n));}", arg=cname, timeout=8000)
        # scrivi come quel personaggio
        pg.evaluate("_setComposeRole('character')")
        pg.evaluate("document.querySelector(\"input[name='compose-role'][value='character']\").checked=true")
        pg.eval_on_selector(
            "#compose-char-select",
            "(el,n)=>{el.value=[...el.options].find(o=>o.text===n).value;}", cname)
        marker = "JBIND_AS_CHAR"
        pg.fill("#scene-compose-text", marker)
        pg.click("#scene-send-btn")
        pg.wait_for_function(
            "(m)=>{const b=document.querySelectorAll('#scene-thread .msg-bubble');"
            "return b.length&&b[b.length-1].innerText.includes(m);}", arg=marker, timeout=8000)
        author = pg.evaluate(
            "()=>{const b=document.querySelectorAll('#scene-thread .msg-bubble');"
            "return (b[b.length-1].querySelector('.msg-author')||{}).textContent;}")
        if author == cname:
            print(f"[PASS] {name}")
        else:
            _FAILS.append(f"{name}: turno non attribuito al personaggio (autore={author!r}, atteso {cname!r})")
    except Exception as e:
        _FAILS.append(f"{name}: {e}")


def journey_write_model_switch(pg):
    """Given scena aperta, When cambio Scrittura a 'Locale', Then l'etichetta modello cambia."""
    name = "WRITE-MODEL-SWITCH"
    pg.goto(f"http://127.0.0.1:{PORT}/", wait_until="domcontentloaded")
    pg.evaluate("showView('scenes')")
    pg.evaluate(f"_loadSceneDetail('{SID}')")
    try:
        pg.wait_for_selector("#write-profile-select", timeout=8000)
        pg.wait_for_function(
            "()=>{const l=document.getElementById('write-model-label');return l&&l.textContent.includes('cerebras');}",
            timeout=8000)
        pg.select_option("#write-profile-select", "local")
        pg.wait_for_function(
            "()=>{const l=document.getElementById('write-model-label');return l&&l.textContent.includes('ollama');}",
            timeout=8000)
        print(f"[PASS] {name}")
    except Exception as e:
        _FAILS.append(f"{name}: lo switch non aggiorna il modello mostrato ({e})")


def journey_refine_injects_rich_sheet(pg):
    """Given un char col card_json vuoto ma scheda RICCA in YAML, When raffino un suo turno,
    Then il prompt inviato al gateway (echo nel pannello) contiene la backstory ricca (GAP-3)."""
    name = "REFINE-INJECTS-RICH-SHEET"
    pg.goto(f"http://127.0.0.1:{PORT}/", wait_until="domcontentloaded")
    pg.evaluate("showView('scenes')")
    pg.evaluate(f"_loadSceneDetail('{SID_SHEET}')")
    try:
        pg.wait_for_selector("#scene-thread .msg-bubble .msg-refine-btn", timeout=8000)
        pg.click("#scene-thread .msg-bubble .msg-refine-btn")
        # lo stub fa echo del prompt: deve contenere la backstory ricca di Galad
        pg.wait_for_function(
            "()=>{const t=document.querySelector('#scene-thread .msg-refined-text');"
            "return t && t.textContent.includes('ghiacci del nord');}", timeout=15000)
        print(f"[PASS] {name}")
    except Exception as e:
        _FAILS.append(f"{name}: il refine NON inietta la scheda ricca nel prompt ({e})")


def journey_created_char_is_bindable(pg):
    """Given creo un personaggio dalla UI, Then è AGGIUNGIBILE al roster di una scena (GAP-6)."""
    name = "CREATED-CHAR-BINDABLE"
    cname = "Char Bindabile JZ"

    def _h(d):
        d.accept(cname) if d.type == "prompt" else d.accept()

    pg.goto(f"http://127.0.0.1:{PORT}/", wait_until="domcontentloaded")
    pg.evaluate("showView('characters')")
    pg.wait_for_selector("#char-new-btn", timeout=8000)
    pg.on("dialog", _h)
    pg.click("#char-new-btn")
    try:
        # il char appena creato deve comparire tra le opzioni del roster-add-select di una scena
        pg.evaluate("showView('scenes')")
        pg.evaluate(f"_loadSceneDetail('{SID_EMPTY}')")
        pg.wait_for_selector("#roster-add-select", timeout=8000)
        pg.wait_for_function(
            "(n)=>[...document.getElementById('roster-add-select').options].some(o=>o.text===n)",
            arg=cname, timeout=8000)
        print(f"[PASS] {name}")
    except Exception as e:
        _FAILS.append(f"{name}: il char creato-da-UI non è bindabile a una scena ({e})")
    finally:
        pg.remove_listener("dialog", _h)


def main():
    chars_dir = tempfile.mkdtemp(prefix="journey-chars-")
    seed(chars_dir)
    gw = HTTPServer(("127.0.0.1", GW_PORT), _GwHandler)
    threading.Thread(target=gw.serve_forever, daemon=True).start()
    env = dict(os.environ, CALLIOPE_DB_PATH=tmp_db, FLASK_PORT=PORT,
               GATEWAY_URL=f"http://127.0.0.1:{GW_PORT}", CALLIOPE_WRITE_FALLBACKS="",
               CALLIOPE_CHARS_DIR=chars_dir)
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
            journey_home_landing(pg)
            journey_message_appends_at_tail(pg)
            journey_refine(pg)
            journey_refine_503_clean(pg)
            journey_create_scene(pg)
            journey_create_character(pg)
            journey_binding_write_as_character(pg)
            journey_write_model_switch(pg)
            journey_refine_injects_rich_sheet(pg)
            journey_created_char_is_bindable(pg)
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
        # crea-personaggio scrive in CALLIOPE_CHARS_DIR (temp isolata) → rimuovo la dir.
        try:
            import shutil
            shutil.rmtree(chars_dir, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
