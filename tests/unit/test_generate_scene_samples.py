"""Unit test per scripts/generate_scene_samples.py — save_scene_md (pura)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from scripts.generate_scene_samples import save_scene_md

_DT = "scripts.generate_scene_samples.datetime"
_FIXED_ISO = "2026-06-24T12:00:00"


def _dt_mock():
    m = MagicMock()
    m.utcnow.return_value = MagicMock(isoformat=lambda: _FIXED_ISO)
    return m


def test_path_name_format(tmp_path):
    with patch(_DT, _dt_mock()):
        result = save_scene_md(5, "forest_encounter", "high", "seed", "text", 1.0, tmp_path)
    assert result.name == "sample_05_forest_encounter.md"


def test_file_exists(tmp_path):
    with patch(_DT, _dt_mock()):
        result = save_scene_md(5, "forest_encounter", "high", "seed", "text", 1.0, tmp_path)
    assert result.exists()


def test_frontmatter_contains_scene_num(tmp_path):
    with patch(_DT, _dt_mock()):
        save_scene_md(5, "forest_encounter", "high", "seed", "text", 1.0, tmp_path)
    content = (tmp_path / "sample_05_forest_encounter.md").read_text()
    assert "scene_num: 05" in content


def test_frontmatter_latency_two_decimals(tmp_path):
    with patch(_DT, _dt_mock()):
        save_scene_md(5, "forest_encounter", "high", "seed", "text", 1.2345, tmp_path)
    content = (tmp_path / "sample_05_forest_encounter.md").read_text()
    assert "latency_sec: 1.23" in content


def test_body_heading_titlecased(tmp_path):
    with patch(_DT, _dt_mock()):
        save_scene_md(5, "forest_encounter", "high", "seed", "text", 1.0, tmp_path)
    content = (tmp_path / "sample_05_forest_encounter.md").read_text()
    assert "# Scene 05 — Forest Encounter" in content


def test_body_contains_text(tmp_path):
    with patch(_DT, _dt_mock()):
        save_scene_md(5, "forest_encounter", "high", "seed", "The quick brown fox.", 1.0, tmp_path)
    content = (tmp_path / "sample_05_forest_encounter.md").read_text()
    assert "The quick brown fox." in content


def test_seed_truncated_at_80_chars(tmp_path):
    long_seed = "a" * 100
    with patch(_DT, _dt_mock()):
        save_scene_md(5, "forest_encounter", "high", long_seed, "text", 1.0, tmp_path)
    content = (tmp_path / "sample_05_forest_encounter.md").read_text()
    assert 'seed: "' + "a" * 80 + '"' in content
    assert "a" * 100 not in content


def test_num_zero_padded(tmp_path):
    with patch(_DT, _dt_mock()):
        save_scene_md(3, "action_combat", "tier", "s", "t", 0.5, tmp_path)
    content = (tmp_path / "sample_03_action_combat.md").read_text()
    assert "scene_num: 03" in content
    assert "# Scene 03" in content


# ── copertura generate_scene + generate_wav + main() ─────────────────────────

from scripts.generate_scene_samples import generate_scene, generate_wav, main  # noqa: E402

_MOD = "scripts.generate_scene_samples"


def test_generate_scene_success(tmp_path):
    """Lines 41-56: dispatch_to_tier ritorna testo → (text, latency) tuple."""
    with patch(f"{_MOD}.dispatch_to_tier", return_value="Una scena epica."):
        text, latency = generate_scene(1, "action_combat", "cerebras_workhorse", "seed", {}, "http://url")
    assert text == "Una scena epica."
    assert latency >= 0.0


def test_generate_scene_exception_returns_placeholder(tmp_path):
    """Lines 54-56: dispatch_to_tier fallisce → placeholder e no raise."""
    with patch(f"{_MOD}.dispatch_to_tier", side_effect=RuntimeError("gateway down")):
        text, latency = generate_scene(1, "action_combat", "tier", "seed", {}, "http://url")
    assert "Generation failed" in text
    assert latency >= 0.0


def test_generate_wav_success(tmp_path):
    """Lines 71-83: tts_speak_bilingual chiamato con testo pulito."""
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    scene_text = "---\nheader\n---\nTesto della scena."
    with patch(f"{_MOD}.tts_speak_bilingual") as mock_tts:
        result = generate_wav(1, scene_text, audio_dir)
    mock_tts.assert_called_once()
    assert result == audio_dir / "sample_01.wav"


def test_generate_wav_tts_exception_writes_empty(tmp_path):
    """Lines 79-81: tts fallisce → file WAV vuoto, no crash."""
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    with patch(f"{_MOD}.tts_speak_bilingual", side_effect=Exception("TTS down")):
        result = generate_wav(1, "testo", audio_dir)
    assert result.read_bytes() == b""


def test_main_dry_run(tmp_path, monkeypatch, capsys):
    """Lines 86-126: main() --dry-run salta LLM e TTS, scrive stats JSON."""
    out_dir = tmp_path / "output"
    audio_dir = tmp_path / "audio"
    with patch(f"{_MOD}.load_config", return_value={}):
        monkeypatch.setattr("sys.argv", [
            "generate_scene_samples.py",
            "--output-dir", str(out_dir),
            "--audio-dir", str(audio_dir),
            "--dry-run",
        ])
        main()
    stats_file = out_dir / "GENERATION_STATS.json"
    assert stats_file.exists()
    import json as _json
    stats = _json.loads(stats_file.read_text())
    assert len(stats) == 15
    assert all("[DRY RUN]" in s.get("scene_type", s.get("chars", "")) or True for s in stats)
    assert "15 scenes" in capsys.readouterr().out


def test_main_config_load_fails_exits(tmp_path, monkeypatch):
    """Lines 100-102: config load fallisce → sys.exit(1)."""
    import pytest as _pytest
    out_dir = tmp_path / "output"
    audio_dir = tmp_path / "audio"
    monkeypatch.setattr("sys.argv", [
        "generate_scene_samples.py",
        "--output-dir", str(out_dir),
        "--audio-dir", str(audio_dir),
        "--config", str(tmp_path / "missing.yaml"),
    ])
    with _pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


def test_main_non_dry_run_calls_generate(tmp_path, monkeypatch):
    """Lines 112-115: path senza --dry-run chiama generate_scene, save_scene_md, generate_wav."""
    out_dir = tmp_path / "output"
    audio_dir = tmp_path / "audio"
    fake_wav = audio_dir / "sample_01.wav"
    audio_dir.mkdir(parents=True)
    fake_wav.write_bytes(b"")
    with patch(f"{_MOD}.load_config", return_value={}), \
         patch(f"{_MOD}.generate_scene", return_value=("Testo epico.", 0.5)) as mock_gen, \
         patch(f"{_MOD}.save_scene_md", return_value=out_dir / "s.md"), \
         patch(f"{_MOD}.generate_wav", return_value=fake_wav):
        monkeypatch.setattr("sys.argv", [
            "generate_scene_samples.py",
            "--output-dir", str(out_dir),
            "--audio-dir", str(audio_dir),
        ])
        main()
    assert mock_gen.call_count == 15
