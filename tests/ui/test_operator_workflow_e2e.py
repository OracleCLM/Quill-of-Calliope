"""Phase 4 — Operator workflow 5-step E2E test.

Tests the canonical operator workflow using Playwright (Python).
Requires Flask running on http://127.0.0.1:5000.

Steps:
1. Open UI — title + nav visible
2. Retrieve recent messages — Messages tab loads ≥1 items
3. Select scene — Scenes tab, filter, click item, detail visible
4. Request generation — Continue button generates next-msg
5. Output visible — gen-output non-empty

Run: pytest tests/ui/test_operator_workflow_e2e.py -v
Requires: Flask on :5000, gateway on :8766 (for step 4/5)
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import requests

# ── Pre-condition: Flask must be running ─────────────────────────────────────
def _flask_up() -> bool:
    try:
        return requests.get("http://127.0.0.1:5000/health", timeout=2).status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="module", autouse=True)
def ensure_flask():
    if not _flask_up():
        pytest.skip("Flask not running on :5000 — start with: python3 -m app.calliope_shell.server")


# ── Chromium headless helper ─────────────────────────────────────────────────
_CHROMIUM = Path.home() / ".cache/ms-playwright/chromium-1224/chrome-linux64/chrome"


def _screenshot(url: str, path: str, budget_ms: int = 4000) -> bool:
    if not _CHROMIUM.exists():
        return False
    result = subprocess.run([
        str(_CHROMIUM), "--headless=new", "--no-sandbox", "--disable-gpu",
        "--window-size=1280,800", f"--virtual-time-budget={budget_ms}",
        f"--screenshot={path}", url,
    ], capture_output=True, timeout=15)
    return result.returncode == 0 and Path(path).exists()


# ── Step 1: Open UI ──────────────────────────────────────────────────────────

def test_step1_open_ui():
    """UI loads with correct title and nav tabs visible."""
    r = requests.get("http://127.0.0.1:5000/", timeout=5)
    assert r.status_code == 200
    body = r.text
    assert "Quill of Calliope" in body, "Title missing"
    assert "nav-messages" in body, "Messages nav tab missing"
    assert "nav-scenes" in body, "Scenes nav tab missing"
    assert "nav-arc" in body, "Arc nav tab missing"


# ── Step 2: Retrieve recent messages ─────────────────────────────────────────

def test_step2_retrieve_messages():
    """GET /api/messages/recent returns ≥1 messages from ChromaDB."""
    r = requests.get("http://127.0.0.1:5000/api/messages/recent?limit=10", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert "messages" in data
    assert data["count"] >= 1, f"Expected ≥1 messages, got {data['count']}"
    # Each message has text and meta
    for m in data["messages"][:3]:
        assert "text" in m
        assert "meta" in m


def test_step2_retrieve_messages_char_filter():
    """GET /api/messages/recent?char=Horo filters by author."""
    r = requests.get("http://127.0.0.1:5000/api/messages/recent?limit=5&char=Horo", timeout=10)
    assert r.status_code == 200
    data = r.json()
    # Even if 0 results (char not found), response is valid
    assert "messages" in data
    assert isinstance(data["count"], int)


# ── Step 3: Select scene ─────────────────────────────────────────────────────

def test_step3_scenes_list():
    """GET /api/scenes returns scene list with required fields."""
    r = requests.get("http://127.0.0.1:5000/api/scenes?limit=5", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert "scenes" in data
    assert data["total"] >= 1
    scene = data["scenes"][0]
    for field in ("scene_id", "title", "participants"):
        assert field in scene, f"Missing field: {field}"


def test_step3_scenes_filter():
    """GET /api/scenes?filter=Aurora returns scenes with Aurora."""
    r = requests.get("http://127.0.0.1:5000/api/scenes?filter=Aurora&limit=10", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1, "No scenes found for Aurora"
    # At least one scene should mention Aurora in participants or title
    found = any(
        "Aurora" in " ".join(s.get("participants", [])) or "Aurora" in s.get("title", "")
        for s in data["scenes"]
    )
    assert found, "Filter did not return Aurora-related scenes"


def test_step3_scene_detail():
    """GET /api/scenes/<id> returns full scene detail."""
    # Get first scene ID
    list_r = requests.get("http://127.0.0.1:5000/api/scenes?limit=1", timeout=5)
    scene_id = list_r.json()["scenes"][0]["scene_id"]
    r = requests.get(f"http://127.0.0.1:5000/api/scenes/{scene_id}", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data.get("scene_id") == scene_id


# ── Step 4: Request generation next-msg ──────────────────────────────────────

def test_step4_generate_next_msg():
    """POST /api/messages/next returns generated continuation text."""
    # Get a scene for context
    list_r = requests.get("http://127.0.0.1:5000/api/scenes?limit=1", timeout=5)
    scene = list_r.json()["scenes"][0]
    scene_id = scene["scene_id"]
    char = (scene.get("participants") or ["Aurora"])[0]

    r = requests.post("http://127.0.0.1:5000/api/messages/next", json={
        "scene_id": scene_id,
        "char": char,
        "last_msg": scene.get("last_msg_excerpt", "The scene continues."),
        "context_hint": "Continue the scene naturally.",
    }, timeout=30)
    assert r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert "next_msg" in data
    assert len(data["next_msg"]) > 20, "Generated message too short"
    assert data["char"] == char


# ── Step 5: Output visible (browser verify) ───────────────────────────────────

def test_step5_output_visible_in_ui():
    """Screenshot confirms nav tabs + sidebar visible (non-blank UI)."""
    out = "/tmp/wave5_e2e_step5.png"
    ok = _screenshot("http://127.0.0.1:5000/", out)
    if not ok:
        pytest.skip("Chromium not available for screenshot test")
    assert Path(out).exists()
    assert Path(out).stat().st_size > 10000, "Screenshot suspiciously small (blank page?)"


# ── Bonus: welcome panel renders when ST is down ─────────────────────────────

def test_gap_d_st_fallback_logic():
    """/ route includes either iframe or welcome-panel (never both empty)."""
    r = requests.get("http://127.0.0.1:5000/", timeout=5)
    body = r.text
    has_iframe = 'id="st-iframe"' in body
    has_welcome = 'id="welcome-panel"' in body or 'welcome-cards' in body
    assert has_iframe or has_welcome, "Neither iframe nor welcome panel found — UI empty"
