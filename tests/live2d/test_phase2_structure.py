"""Phase-2 structure smoke tests — file existence + JS syntax (node --check)."""
from __future__ import annotations
import json
import shutil
import subprocess
from pathlib import Path
import pytest

LIVE2D = Path(__file__).parent.parent.parent / "frontend" / "live2d"
SCRIPTS = Path(__file__).parent.parent.parent / "scripts"

PHASE2_JS = [
    "expressions.js",
    "emotion_transitions.js",
    "phoneme_sync.js",
    "persistent_state.js",
]

@pytest.mark.parametrize("fname", PHASE2_JS)
def test_phase2_js_exists(fname):
    assert (LIVE2D / fname).exists(), f"Missing: {fname}"

@pytest.mark.parametrize("fname", PHASE2_JS)
def test_phase2_js_syntax(fname):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    r = subprocess.run([node, "--check", str(LIVE2D / fname)], capture_output=True, text=True)
    assert r.returncode == 0, f"Syntax error in {fname}:\n{r.stderr}"

def test_tts_phoneme_export_exists():
    assert (SCRIPTS / "tts_phoneme_export.py").exists()

def test_tts_phoneme_export_cli_graceful():
    r = subprocess.run(
        ["python3", str(SCRIPTS / "tts_phoneme_export.py"), "Hello", "--json-only"],
        capture_output=True, text=True, cwd=SCRIPTS.parent
    )
    assert r.returncode == 0
    import json
    lines = r.stdout.strip().splitlines()
    j_start = next((i for i, ln in enumerate(lines) if ln.strip().startswith("{")), 0)
    d = json.loads("\n".join(lines[j_start:]))
    assert "phonemes" in d
    assert "text" in d

def test_phase2_js_api_surface():
    """Verify key global APIs are exported in each file."""
    checks = {
        "expressions.js": ["setExpression", "EXPRESSIONS"],
        "emotion_transitions.js": ["EmotionTransitionManager", "TRANSITION_MATRIX"],
        "phoneme_sync.js": ["PhonemeSyncManager", "PHONEME_MOUTH_SHAPES"],
        "persistent_state.js": ["saveMascotState", "loadMascotState"],
    }
    for fname, apis in checks.items():
        src = (LIVE2D / fname).read_text(encoding="utf-8")
        for api in apis:
            assert api in src, f"{fname} missing API: {api}"


# --- Phase-2 phoneme fixture tests (Task B — R-CALLIOPE-PHONEME-SYNC-VERIFY-REAL-ESPEAK) ---

def test_phoneme_fixture_exists():
    phoneme_path = LIVE2D / "test_data" / "sample_phonemes.json"
    assert phoneme_path.exists()


def test_phoneme_fixture_schema():
    phoneme_path = LIVE2D / "test_data" / "sample_phonemes.json"
    with open(phoneme_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "text" in data and "phonemes" in data and "wav_b64" in data
    assert isinstance(data["phonemes"], list) and len(data["phonemes"]) > 5
    for phoneme in data["phonemes"]:
        assert {"phoneme", "start_ms", "end_ms"} <= phoneme.keys()
        assert phoneme["start_ms"] >= 0
        assert phoneme["end_ms"] > phoneme["start_ms"]


def test_phoneme_fixture_has_vowels():
    phoneme_path = LIVE2D / "test_data" / "sample_phonemes.json"
    data = json.loads(phoneme_path.read_text(encoding="utf-8"))
    vowels = "aeiouæɛɪʊɔʌɑɐəɜɒ"
    phoneme_chars = [p["phoneme"] for p in data["phonemes"]]
    assert any(char in vowels for char in phoneme_chars)
