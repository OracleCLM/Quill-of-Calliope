"""Fase 3+4 — verify the shared mascot package is consumable by a second repo (Vesta).

Simulates Vesta's consumption per VESTA_IMPORT_PATH.md: import the WS server app and
the phoneme export via the shared sys.path, and confirm the frontend scaffold (template
+ renderer + core JS) is present and self-contained. No Vesta repo is touched.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

SHARED_ROOT = Path(__file__).parent.parent.parent  # .../shared
PKG = SHARED_ROOT / "live2d_mascot"
FRONTEND = PKG / "frontend"
TEMPLATE = FRONTEND / "index.template.html"


# ── Fase 3: shared HTML template ──────────────────────────────────────────────

class TestSharedTemplate:
    def test_template_exists(self):
        assert TEMPLATE.exists()

    def test_template_has_canvas_and_controls(self):
        html = TEMPLATE.read_text()
        assert "live2d-canvas" in html
        for state in ("idle", "talking", "listening", "thinking"):
            assert f"setMascotState('{state}')" in html

    def test_template_is_repo_agnostic(self):
        """Template must use placeholders, not Calliope-specific values."""
        html = TEMPLATE.read_text()
        assert "{{MODEL_URL}}" in html
        assert "{{ENGINE_CUBISM_CORE}}" in html
        assert "calliope" not in html.lower()
        assert "hiyori" not in html.lower()

    def test_template_loads_shared_renderer(self):
        html = TEMPLATE.read_text()
        assert "core/renderer.js" in html
        assert "createMascotRenderer" in html
        assert "window.MASCOT_CONFIG" in html


# ── Fase 4: Vesta import path (Python side) ───────────────────────────────────

class TestVestaImportPath:
    def test_ws_server_importable_via_shared_path(self):
        """Vesta does: sys.path.insert(0, <shared>); from live2d_mascot... import app."""
        if str(SHARED_ROOT) not in sys.path:
            sys.path.insert(0, str(SHARED_ROOT))
        mod = importlib.import_module("live2d_mascot.server.ws_server")
        assert hasattr(mod, "app")
        assert hasattr(mod, "main")

    def test_phoneme_export_importable_via_shared_path(self):
        """Phoneme export is now shared infra — Vesta can reuse it too."""
        if str(SHARED_ROOT) not in sys.path:
            sys.path.insert(0, str(SHARED_ROOT))
        mod = importlib.import_module("live2d_mascot.server.tts_phoneme_export")
        assert hasattr(mod, "export_phonemes")
        # graceful contract: returns the expected keys even without espeak/audio
        result = mod.export_phonemes("hi", output_dir="/tmp")
        assert set(result.keys()) == {"wav_b64", "phonemes", "text"}

    def test_frontend_core_self_contained(self):
        """All JS the template references must exist in the shared package."""
        core = FRONTEND / "core"
        for fname in ("state_machine.js", "tts_sync.js", "expressions.js", "renderer.js"):
            assert (core / fname).exists(), f"template references missing {fname}"


# ── Fase 4: scripts/ shim still works (no Calliope breakage) ──────────────────

class TestCalliopeShimIntact:
    def test_scripts_reexport_resolves(self):
        repo_root = SHARED_ROOT.parent
        scripts = repo_root / "scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        # importing the shim must expose export_phonemes (re-exported from shared)
        shim = importlib.import_module("tts_phoneme_export")
        assert hasattr(shim, "export_phonemes")
