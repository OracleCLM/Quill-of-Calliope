"""Tests for scene library expansion — config, samples, WAV bundle, continuity."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

CONFIG_PATH = ROOT / "data" / "llm_routing_config.yaml"
SAMPLES_DIR = ROOT / "scenes" / "m3_library_samples"
AUDIO_DIR = SAMPLES_DIR / "audio"

EXPECTED_TYPES = [
    "action_combat", "character_death", "romantic_fade_to_black", "lore_exposition",
    "action_aftermath", "comedic_banter", "mystery_investigation", "exploration_landscape",
    "intimate_dialogue", "transition_temporal", "flashback_memory", "dream_surreal",
    "ritual_ceremony", "combat_chase", "ooc_meta", "nsfw_explicit", "climax_rare",
    "system_command", "default",
]


class TestConfigExpansion:
    def test_config_loads_clean(self):
        config = yaml.safe_load(CONFIG_PATH.read_text())
        assert "matrix" in config
        assert "nsfw_threshold" in config
        assert "block_thresholds" in config

    def test_all_new_types_present(self):
        config = yaml.safe_load(CONFIG_PATH.read_text())
        matrix = config["matrix"]
        new_types = [
            "action_aftermath", "comedic_banter", "mystery_investigation",
            "exploration_landscape", "intimate_dialogue", "transition_temporal",
            "flashback_memory", "dream_surreal", "ritual_ceremony", "combat_chase",
        ]
        for t in new_types:
            assert t in matrix, f"Missing scene type: {t}"

    def test_total_types_gte_18(self):
        config = yaml.safe_load(CONFIG_PATH.read_text())
        assert len(config["matrix"]) >= 18

    def test_tier_fields_complete(self):
        config = yaml.safe_load(CONFIG_PATH.read_text())
        for name, entry in config["matrix"].items():
            assert "tier" in entry, f"{name} missing tier"
            assert "provider" in entry, f"{name} missing provider"
            assert "model" in entry, f"{name} missing model"

    def test_new_types_valid_providers(self):
        valid_providers = {"cerebras", "groq", "openrouter", "ollama", "claude"}
        config = yaml.safe_load(CONFIG_PATH.read_text())
        new_types = ["action_aftermath", "comedic_banter", "mystery_investigation",
                     "exploration_landscape", "intimate_dialogue"]
        for t in new_types:
            provider = config["matrix"][t]["provider"]
            assert provider in valid_providers, f"{t}: invalid provider {provider}"


class TestSampleGeneration:
    def test_sample_md_files_exist(self):
        md_files = list(SAMPLES_DIR.glob("sample_*.md"))
        assert len(md_files) >= 14, f"Expected ≥14 MD files, got {len(md_files)}"

    def test_sample_md_has_frontmatter(self):
        md_files = sorted(SAMPLES_DIR.glob("sample_*.md"))
        for f in md_files[:3]:  # Check first 3
            content = f.read_text()
            assert content.startswith("---"), f"{f.name} missing frontmatter"
            assert "scene_type:" in content
            assert "tier:" in content

    def test_stats_json_present(self):
        stats_path = SAMPLES_DIR / "GENERATION_STATS.json"
        assert stats_path.exists()
        stats = json.loads(stats_path.read_text())
        assert len(stats) == 15
        assert all("scene_type" in s for s in stats)
        assert all("latency_sec" in s for s in stats)

    def test_generate_scene_mock(self):
        """Test generate_scene_samples in dry-run mode."""
        import subprocess
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_scene_samples.py"), "--dry-run"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        assert result.returncode == 0, f"dry-run failed: {result.stderr}"
        assert "Done" in result.stdout or "Done" in result.stderr


class TestWAVBundle:
    def test_wav_files_exist(self):
        wav_files = list(AUDIO_DIR.glob("sample_*.wav"))
        assert len(wav_files) >= 14, f"Expected ≥14 WAV files, got {len(wav_files)}"

    def test_wav_files_nonzero(self):
        wav_files = sorted(AUDIO_DIR.glob("sample_*.wav"))
        nonzero = [f for f in wav_files if f.stat().st_size > 1000]
        assert len(nonzero) >= 13, f"Expected ≥13 non-empty WAV, got {len(nonzero)}"

    def test_wav_valid_riff(self):
        import wave, io
        wav_files = sorted(AUDIO_DIR.glob("sample_*.wav"))
        valid = 0
        for f in wav_files:
            if f.stat().st_size < 44:
                continue
            try:
                with wave.open(str(f)) as wf:
                    assert wf.getframerate() in (8000, 16000, 22050, 44100)
                    valid += 1
            except Exception:
                pass
        assert valid >= 13, f"Expected ≥13 valid RIFF WAV, got {valid}"


class TestContinuityTester:
    def test_continuity_script_dry_run(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "test_narrative_continuity.py"),
             "--dry-run", "--output", "/tmp/calliope_test_continuity.md"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        assert result.returncode == 0, f"continuity dry-run failed: {result.stderr}"
        assert "chain" in result.stdout.lower() or "continuity" in result.stdout.lower()

    def test_continuity_report_generated(self):
        report = ROOT / ".planning" / "CONTINUITY_REPORT.md"
        assert report.exists(), "CONTINUITY_REPORT.md not generated"
        content = report.read_text()
        assert "Chain length" in content or "chain" in content.lower()
        assert "Avg char continuity" in content or "continuity" in content.lower()
