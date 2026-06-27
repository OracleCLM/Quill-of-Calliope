"""Smoke tests for shared/live2d_mascot — repo-agnostic infra.

Tests: file structure, WS server import, JS core content, protocol schema.
No real network calls — verifies package integrity.
"""
from __future__ import annotations

import sys
from pathlib import Path


SHARED = Path(__file__).parent.parent
FRONTEND_CORE = SHARED / "frontend" / "core"
SERVER = SHARED / "server"

# Wire sys.path for import
if str(SHARED.parent) not in sys.path:
    sys.path.insert(0, str(SHARED.parent))


# ── 1. Package structure ──────────────────────────────────────────────────────

class TestPackageStructure:
    def test_server_ws_server_exists(self):
        assert (SERVER / "ws_server.py").exists()

    def test_frontend_core_files_exist(self):
        required = ["state_machine.js", "emotion_transitions.js", "expressions.js",
                    "phoneme_sync.js", "persistent_state.js", "tts_sync.js"]
        for fname in required:
            assert (FRONTEND_CORE / fname).exists(), f"Missing: {fname}"

    def test_architecture_doc_exists(self):
        assert (SHARED / "docs" / "ARCHITECTURE.md").exists()

    def test_vesta_import_path_doc_exists(self):
        assert (SHARED / "VESTA_IMPORT_PATH.md").exists()


# ── 2. WS server Python import ────────────────────────────────────────────────

class TestWSServerImport:
    def test_import_succeeds(self):
        from live2d_mascot.server.ws_server import app, manager  # noqa: PLC0415
        assert app is not None
        assert manager is not None

    def test_app_title(self):
        from live2d_mascot.server.ws_server import app  # noqa: PLC0415
        assert "mascot" in app.title.lower()

    def test_connection_manager_starts_empty(self):
        from live2d_mascot.server.ws_server import ConnectionManager  # noqa: PLC0415
        mgr = ConnectionManager()
        assert len(mgr.active_connections) == 0

    def test_pydantic_models_importable(self):
        from live2d_mascot.server.ws_server import StateEvent, EmotionEvent, TtsEvent  # noqa: PLC0415
        ev = StateEvent(state="talking")
        assert ev.state == "talking"
        em = EmotionEvent(emotion="happy")
        assert em.emotion == "happy"
        tt = TtsEvent(type="start", data={"text": "hello"})
        assert tt.type == "start"

    def test_health_route_registered(self):
        from live2d_mascot.server.ws_server import app  # noqa: PLC0415
        routes = [r.path for r in app.routes]
        assert "/health" in routes

    def test_event_routes_registered(self):
        from live2d_mascot.server.ws_server import app  # noqa: PLC0415
        routes = [r.path for r in app.routes]
        for path in ("/event/state", "/event/emotion", "/event/tts"):
            assert path in routes, f"Missing route: {path}"


# ── 3. JS core content validation ─────────────────────────────────────────────

class TestJSCoreContent:
    def test_state_machine_exports_set_mascot_state(self):
        content = (FRONTEND_CORE / "state_machine.js").read_text()
        assert "setMascotState" in content
        assert "idle" in content and "talking" in content

    def test_expressions_map_to_mao_slots(self):
        # expressions.js maps emotions (joy/sad/anger/surprise/neutral/thinking/confused)
        # onto the SHIPPABLE Mao model's real expression Names (exp_01..exp_08).
        content = (FRONTEND_CORE / "expressions.js").read_text()
        for emotion in ("neutral", "sad", "surprise", "thinking", "confused"):
            assert emotion in content.lower(), f"Missing emotion: {emotion}"
        # Real Mao expression slots, not the old placeholder f00..f06.
        assert "exp_01" in content and "exp_08" in content
        assert "f06" not in content

    def test_tts_sync_has_param_mouth(self):
        content = (FRONTEND_CORE / "tts_sync.js").read_text()
        assert "ParamMouthOpenY" in content

    def test_phoneme_sync_has_timing_mechanism(self):
        # phoneme_sync uses setTimeout-based scheduling (not rAF)
        content = (FRONTEND_CORE / "phoneme_sync.js").read_text()
        assert "setTimeout" in content or "requestAnimationFrame" in content

    def test_persistent_state_uses_localstorage(self):
        content = (FRONTEND_CORE / "persistent_state.js").read_text()
        assert "localStorage" in content


# ── 4. Protocol schema ────────────────────────────────────────────────────────

class TestWSProtocol:
    VALID_STATES = {"idle", "talking", "listening", "thinking"}

    def test_state_machine_valid_states_defined(self):
        content = (FRONTEND_CORE / "state_machine.js").read_text()
        for s in self.VALID_STATES:
            assert s in content, f"State not found in state_machine.js: {s}"

    def test_architecture_doc_covers_protocol(self):
        arch = (SHARED / "docs" / "ARCHITECTURE.md").read_text()
        assert "SET_STATE" in arch
        assert "SET_EXPRESSION" in arch
        assert "/health" in arch


# ── 5. Calliope thin wrapper ──────────────────────────────────────────────────

class TestCalliopeThinWrapper:
    SCRIPTS = SHARED.parent.parent / "scripts"

    def test_mascot_ws_server_imports_shared(self):
        content = (self.SCRIPTS / "mascot_ws_server.py").read_text()
        assert "live2d_mascot" in content or "shared" in content

    def test_mascot_ws_server_still_has_main(self):
        content = (self.SCRIPTS / "mascot_ws_server.py").read_text()
        assert "def main" in content
