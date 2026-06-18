#!/usr/bin/env python3
"""Real-browser render verification for the Live2D mascot shell.

Loads the dev dashboard (frontend/live2d/index.html) for each model with the REAL
Live2D/PIXI engine (no mock) and confirms, per model:
  1. the shared renderer mounts the model     → window.mascotApp.model is set
  2. idle/blink/breath loop is running         → an animated param value changes
  3. at least one expression change applies     → model.expression(<real name>) ok
and saves a screenshot for aesthetic review.

Run:  python3 scripts/verify_mascot_render.py
Needs network (engine scripts load from CDN) + playwright chromium.
"""
from __future__ import annotations

import http.server
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / ".planning" / "mascot_verify"
MODELS = ["mao", "koko", "tingyun"]
PORT = 8799


def _serve():
    def handler(*a, **k):
        return http.server.SimpleHTTPRequestHandler(*a, directory=str(REPO), **k)
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def verify_model(page, key: str) -> dict:
    url = f"http://127.0.0.1:{PORT}/frontend/live2d/index.html?model={key}"
    errors: list[str] = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(url, wait_until="load")

    # 1. model mounted
    page.wait_for_function("() => window.mascotApp && window.mascotApp.model", timeout=20000)

    # 2. animated idle loop running — sample ParamBreath over ~4s and check the
    #    value oscillates (breath is auto-applied by pixi-live2d-display).
    sample = """() => {
        const m = window.mascotApp.model.internalModel.coreModel;
        const ids = ['ParamBreath','ParamEyeLOpen','ParamAngleX','ParamAngleY'];
        const out = {};
        for (const id of ids) { try { out[id] = m.getParameterValueById(id); } catch(e){} }
        return out;
    }"""
    series: dict[str, list[float]] = {}
    for _ in range(16):
        snap = page.evaluate(sample)
        for k, v in snap.items():
            series.setdefault(k, []).append(v or 0.0)
        page.wait_for_timeout(250)
    ranges = {k: (max(v) - min(v)) for k, v in series.items()}
    animated = any(r > 1e-3 for r in ranges.values())

    # 3. expression change — use the real names from the active registry
    expr_result = page.evaluate("""async () => {
        const exprs = (window.MASCOT_ACTIVE && window.MASCOT_ACTIVE.expressions) || [];
        if (!exprs.length) return {ok:false, name:null, n:0};
        const name = exprs[Math.min(1, exprs.length-1)];
        try { window.mascotApp.model.expression(name); return {ok:true, name, n:exprs.length}; }
        catch(e){ return {ok:false, name, n:exprs.length, err:String(e)}; }
    }""")
    page.wait_for_timeout(900)

    # Frame the whole figure for an aesthetic-review screenshot (head→body),
    # overriding the renderer's centered framing which crops tall models to the torso.
    page.evaluate("""() => {
        const {app, model} = window.mascotApp;
        const b = model.getLocalBounds();
        const margin = 0.92;
        const s = Math.min(app.screen.width / b.width, app.screen.height / b.height) * margin;
        model.scale.set(s);
        model.anchor.set(0.5, 0);
        model.position.set(app.screen.width / 2, app.screen.height * 0.04);
    }""")
    page.wait_for_timeout(600)

    OUT.mkdir(parents=True, exist_ok=True)
    shot = OUT / f"mascot_{key}.png"
    page.screenshot(path=str(shot))
    renders = _screenshot_has_content(shot)

    return {
        "model": key,
        "mounted": True,
        "renders": renders,
        "animated_idle": animated,
        "param_ranges": {k: round(v, 4) for k, v in ranges.items()},
        "expression": expr_result,
        "screenshot": str(shot),
        "console_errors": [e for e in errors if "8767" not in e and "CORS" not in e][:3],
    }


def _screenshot_has_content(path: Path) -> bool:
    """True if the screenshot is not a flat/near-uniform image (i.e. the model drew)."""
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        return path.stat().st_size > 20000  # heuristic fallback: a drawn canvas PNG is large
    img = Image.open(path).convert("RGB")
    colors = img.getcolors(maxcolors=100000)
    if not colors:
        return True  # too many colors → definitely content
    # uniform background would be ~1 dominant color covering nearly all pixels
    total = sum(c for c, _ in colors)
    dominant = max(c for c, _ in colors)
    return (dominant / total) < 0.985


def main() -> int:
    httpd = _serve()
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--use-gl=swiftshader", "--ignore-gpu-blocklist"])
            ctx = browser.new_context(viewport={"width": 600, "height": 900})
            for key in MODELS:
                page = ctx.new_page()
                try:
                    results.append(verify_model(page, key))
                except Exception as exc:  # noqa: BLE001
                    results.append({"model": key, "mounted": False, "error": str(exc)})
                page.close()
            browser.close()
    finally:
        httpd.shutdown()

    ok = True
    print("\n=== MASCOT RENDER VERIFY ===")
    for r in results:
        passed = (r.get("mounted") and r.get("renders")
                  and r.get("animated_idle") and r.get("expression", {}).get("ok"))
        ok = ok and passed
        mark = "✅" if passed else "❌"
        print(f"{mark} {r['model']}: mounted={r.get('mounted')} renders={r.get('renders')} "
              f"idle/breath={r.get('animated_idle')} "
              f"expr={r.get('expression', {}).get('name')}({r.get('expression', {}).get('ok')}) "
              f"shot={r.get('screenshot','-')}")
        if r.get("param_ranges"):
            print(f"    param_ranges: {r['param_ranges']}")
        if r.get("error"):
            print(f"    error: {r['error']}")
        if r.get("console_errors"):
            print(f"    console: {r['console_errors']}")
    print("=== RESULT:", "ALL PASS" if ok else "FAILURES", "===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
