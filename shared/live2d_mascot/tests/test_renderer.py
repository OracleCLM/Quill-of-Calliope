"""Structure tests for the shared mascot renderer (renderer.js).

Verifies the renderer factory exists, is parameterized (no hardcoded model URL),
and honours the downstream contract that the 6 core JS files depend on:
  window.mascotApp = { app, model }, mascotReady event, ParamMouthOpenY, model.expression.
"""
from __future__ import annotations

from pathlib import Path

FRONTEND_CORE = Path(__file__).parent.parent / "frontend" / "core"
RENDERER = FRONTEND_CORE / "renderer.js"


class TestRendererExists:
    def test_renderer_file_exists(self):
        assert RENDERER.exists(), "renderer.js missing from shared frontend/core"

    def test_exposes_factory(self):
        js = RENDERER.read_text()
        assert "createMascotRenderer" in js
        assert "function createMascotRenderer" in js


class TestRendererParameterized:
    """The whole point of extraction: no Calliope/Hiyori-specific hardcoding."""

    def test_takes_model_url_config(self):
        js = RENDERER.read_text()
        assert "config.modelUrl" in js or "modelUrl" in js

    def test_no_hardcoded_cdn_model(self):
        js = RENDERER.read_text().lower()
        # the original app.js hardcoded a jsdelivr Hiyori URL — must not leak here
        assert "cdn.jsdelivr.net" not in js
        assert "hiyori" not in js

    def test_canvas_id_configurable(self):
        js = RENDERER.read_text()
        assert "canvasId" in js


class TestRendererContract:
    """Downstream JS (state_machine/tts_sync/expressions) depend on this surface."""

    def test_sets_mascot_app_global(self):
        js = RENDERER.read_text()
        assert "window.mascotApp" in js
        assert "app" in js and "model" in js

    def test_dispatches_mascot_ready(self):
        js = RENDERER.read_text()
        assert "mascotReady" in js
        assert "CustomEvent" in js

    def test_loads_model_via_live2d(self):
        js = RENDERER.read_text()
        assert "Live2DModel.from" in js

    def test_plays_idle_motion(self):
        js = RENDERER.read_text()
        assert "idleMotion" in js or "model.motion" in js

    def test_exports_for_consumers(self):
        js = RENDERER.read_text()
        # browser global + CommonJS so consumers (and tests) can load it
        assert "window.createMascotRenderer" in js
        assert "module.exports" in js
