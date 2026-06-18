#!/usr/bin/env python3
"""Browser-verify the mascot on the REAL Calliope product home (not the dev harness).

Opens the Flask shell home, waits for the shared renderer to publish
window.mascotApp.model + the 'mascotReady' event, asserts the mascot canvas
actually rendered non-blank pixels, and screenshots the home.

Usage:  python .planning/mascot_verify/verify_home_mascot.py [base_url]
RAM-aware: single browser process, headless.
"""
import sys
import pathlib

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5055"
OUT = pathlib.Path(__file__).parent / "home_calliope.png"


def main():
    logs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.on("console", lambda m: logs.append(f"[{m.type}] {m.text}"))
        page.on("pageerror", lambda e: logs.append(f"[pageerror] {e}"))

        page.goto(BASE, wait_until="networkidle", timeout=30000)

        # The mascot sidebar lives in the "Home" view (default landing is Dashboard).
        # Navigate to the real Home so the mascot is actually on-screen.
        page.click("#nav-home")
        page.wait_for_timeout(800)

        # Wait for the shared renderer to mount the model (contract: window.mascotApp.model).
        ready = False
        try:
            page.wait_for_function(
                "() => window.mascotApp && window.mascotApp.model",
                timeout=20000,
            )
            ready = True
        except Exception:
            ready = False

        # Inspect what actually loaded.
        info = page.evaluate(
            """() => {
                const c = document.getElementById('mascot');
                let nonBlank = false;
                try {
                    const g = document.createElement('canvas');
                    g.width = c.width; g.height = c.height;
                    // Pixi uses webgl; read back via toDataURL length as a blank-vs-drawn proxy.
                    const data = c.toDataURL();
                    nonBlank = data.length > 5000;
                } catch (e) {}
                return {
                    hasCanvas: !!c,
                    canvasW: c ? c.width : null,
                    canvasH: c ? c.height : null,
                    hasMascotApp: !!window.mascotApp,
                    hasModel: !!(window.mascotApp && window.mascotApp.model),
                    activeKey: window.MASCOT_ACTIVE ? window.MASCOT_ACTIVE.key : null,
                    activeUrl: window.MASCOT_ACTIVE ? window.MASCOT_ACTIVE.modelUrl : null,
                    rendererFn: typeof window.createMascotRenderer,
                    dataUrlNonBlank: nonBlank,
                };
            }"""
        )

        page.screenshot(path=str(OUT), full_page=False)
        browser.close()

    print("=== CONSOLE / PAGE LOGS ===")
    for line in logs:
        print(line)
    print("=== RENDER INFO ===")
    for k, v in info.items():
        print(f"  {k}: {v}")
    print(f"=== mascotReady (model mounted): {ready} ===")
    print(f"=== screenshot: {OUT} ===")

    ok = ready and info.get("hasModel") and info.get("dataUrlNonBlank")
    print(f"=== VERDICT: {'PASS' if ok else 'FAIL'} ===")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
