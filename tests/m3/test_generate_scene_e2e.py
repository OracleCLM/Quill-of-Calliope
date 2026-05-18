"""E2E test for scripts/generate_scene.py.

Unit test (mocked) — fast CI path.
Integration tests (@pytest.mark.integration) — skip if gateway localhost:8766 is down.
Audit fix: AP1 Mock Loop Fallacy — was MISSING-REAL-TEST.
Fixed 2026-05-18 (sprint R-CALLIOPE-AUDIT-FIX-FALSE-POSITIVES-TOP1).
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

SCRIPTS_DIR = Path(__file__).parents[2] / "scripts"
GATEWAY_URL = "http://localhost:8766"


# ── Gateway availability ──────────────────────────────────────────────────────

def _gateway_available() -> bool:
    try:
        return requests.get(f"{GATEWAY_URL}/health", timeout=2).status_code == 200
    except Exception:
        return False


skip_if_gateway_down = pytest.mark.skipif(
    not _gateway_available(),
    reason="Gateway localhost:8766 not available",
)


# ── Unit test (mocked) — fast CI ─────────────────────────────────────────────

@pytest.mark.unit
def test_generate_scene_e2e(tmp_path: Path) -> None:
    """Mock-based: verify .md output format with stub LLM response."""
    output_file = tmp_path / "out.md"

    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))

    with patch("route_scene.dispatch_to_tier", return_value="A great battle unfolds."):
        import generate_scene as gs_module  # noqa: PLC0415
        importlib.reload(gs_module)

        old_argv = sys.argv
        sys.argv = ["generate_scene.py", "--scene-type", "action_combat",
                    "--prompt", "Two warriors clash at dawn.", "--output", str(output_file)]
        try:
            with pytest.raises(SystemExit) as exc_info:
                gs_module.main()
        finally:
            sys.argv = old_argv

    assert exc_info.value.code == 0
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "action_combat" in content
    assert "A great battle unfolds." in content
    assert "**Latency**:" in content
    assert "Calliope.AI M3" in content


# ── Integration tests — real gateway ─────────────────────────────────────────

@skip_if_gateway_down
@pytest.mark.integration
def test_gateway_health_real() -> None:
    """Real GET /health → status ok + providers list."""
    r = requests.get(f"{GATEWAY_URL}/health", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    assert isinstance(data.get("providers"), list)
    assert len(data["providers"]) >= 1


@skip_if_gateway_down
@pytest.mark.integration
def test_scene_gen_cerebras_real() -> None:
    """Real POST /llm_code provider=cerebras → non-empty text response."""
    r = requests.post(f"{GATEWAY_URL}/llm_code", json={
        "provider": "cerebras",
        "prompt": "Write one sentence of fantasy RP prose.",
        "max_tokens": 64, "temperature": 0.5,
    }, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "content" in data
    assert isinstance(data["content"], str) and len(data["content"].strip()) > 5
    assert data.get("provider") == "cerebras"
    assert data.get("model", "")  # non-empty model name


@skip_if_gateway_down
@pytest.mark.integration
def test_scene_gen_groq_real() -> None:
    """Real POST /llm_ask provider=groq → non-empty response."""
    r = requests.post(f"{GATEWAY_URL}/llm_ask", json={
        "provider": "groq",
        "prompt": "Say exactly: hello calliope",
        "max_tokens": 32, "temperature": 0.1,
    }, timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert len(data.get("content", "").strip()) > 0
    assert data.get("provider") == "groq"


@skip_if_gateway_down
@pytest.mark.integration
def test_route_scene_real_e2e(tmp_path: Path) -> None:
    """Full pipeline: route_scene(ooc_meta) → dispatch groq → markdown written."""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))

    from route_scene import DEFAULT_CONFIG, dispatch_to_tier, route_scene  # noqa: PLC0415

    routing = route_scene(
        "ooc_meta",
        {"nudity_explicit": 0, "violence_gore": 0, "non_consent": 0, "minors_adjacent": 0},
        config=DEFAULT_CONFIG,
    )
    assert routing["provider"] == "groq"

    result = dispatch_to_tier(
        tier_name=routing["tier"],
        prompt="[OOC] Players checking HP totals.",
        config=DEFAULT_CONFIG,
        gateway_url=GATEWAY_URL,
        timeout=20, max_retries=1,
    )
    assert isinstance(result, str) and len(result.strip()) > 10

    out = tmp_path / "scene_ooc.md"
    out.write_text(f"# Scene: ooc_meta\n\n{result}\n", encoding="utf-8")
    assert out.exists() and out.stat().st_size > 0
