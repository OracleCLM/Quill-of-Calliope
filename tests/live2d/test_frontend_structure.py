"""Smoke tests for frontend/live2d/ structure — file existence + HTTP 200."""
from __future__ import annotations

import http.server
import threading
import time
import urllib.request
from pathlib import Path

FRONTEND = Path(__file__).parent.parent.parent / "frontend" / "live2d"
TEST_PORT = 18080


def _start_server():
    import os
    os.chdir(Path(__file__).parent.parent.parent)
    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *a, **k: None  # silence
    srv = http.server.HTTPServer(("127.0.0.1", TEST_PORT), handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    time.sleep(0.3)
    return srv


class TestFrontendStructure:
    def test_required_files_exist(self):
        required = ["index.html", "app.js", "state_machine.js", "tts_sync.js", "style.css", "README.md"]
        for fname in required:
            assert (FRONTEND / fname).exists(), f"Missing: {fname}"

    def test_index_html_has_canvas(self):
        html = (FRONTEND / "index.html").read_text()
        assert "live2d-canvas" in html
        assert "pixi.js" in html.lower() or "pixi" in html.lower()
        assert "cubism4.min.js" in html or "pixi-live2d-display" in html

    def test_state_machine_exports_function(self):
        js = (FRONTEND / "state_machine.js").read_text()
        assert "setMascotState" in js
        assert "idle" in js
        assert "talking" in js
        assert "listening" in js
        assert "thinking" in js

    def test_tts_sync_has_class(self):
        js = (FRONTEND / "tts_sync.js").read_text()
        assert "TTSSync" in js
        assert "attachToAudio" in js
        assert "ParamMouthOpenY" in js
        assert "requestAnimationFrame" in js

    def test_app_js_uses_shared_renderer(self):
        """app.js is now a thin config wrapper delegating to the shared renderer."""
        js = (FRONTEND / "app.js").read_text()
        assert "createMascotRenderer" in js
        assert "modelUrl" in js
        assert "model3.json" in js  # placeholder/config model URL

    def test_index_loads_shared_renderer(self):
        html = (FRONTEND / "index.html").read_text()
        assert "renderer.js" in html
        # loaded before app.js so the factory is defined when app.js runs
        assert html.index("renderer.js") < html.index("app.js")

    def test_http_server_serves_index(self):
        srv = _start_server()
        try:
            url = f"http://127.0.0.1:{TEST_PORT}/frontend/live2d/index.html"
            with urllib.request.urlopen(url, timeout=5) as resp:
                assert resp.status == 200
                content = resp.read().decode()
                assert "live2d-canvas" in content
        finally:
            srv.shutdown()
