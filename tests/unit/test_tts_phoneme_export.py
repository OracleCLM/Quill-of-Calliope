"""Unit test per scripts/tts_phoneme_export.py — estimate_timing (pura)."""
from __future__ import annotations

from scripts.tts_phoneme_export import PHONEME_DURATION_MS, estimate_timing


def test_empty_list():
    assert estimate_timing([]) == []


def test_single_known_phoneme():
    # "a" = 120ms nel dict reale
    result = estimate_timing(["a"])
    assert result == [{"phoneme": "a", "start_ms": 0, "end_ms": 120}]


def test_single_unknown_phoneme_uses_default():
    default = PHONEME_DURATION_MS["default"]
    result = estimate_timing(["xyz"])
    assert result == [{"phoneme": "xyz", "start_ms": 0, "end_ms": default}]


def test_multiple_phonemes_cumulative():
    # "a"=120, "i"=90, "o"=110
    result = estimate_timing(["a", "i", "o"])
    assert result[0] == {"phoneme": "a", "start_ms": 0, "end_ms": 120}
    assert result[1] == {"phoneme": "i", "start_ms": 120, "end_ms": 210}
    assert result[2] == {"phoneme": "o", "start_ms": 210, "end_ms": 320}


def test_end_ms_equals_next_start_ms():
    result = estimate_timing(["a", "e", "u"])
    for i in range(len(result) - 1):
        assert result[i]["end_ms"] == result[i + 1]["start_ms"]


def test_total_duration_cumulative():
    phonemes = ["a", "i"]  # 120+90=210
    result = estimate_timing(phonemes)
    assert result[-1]["end_ms"] == 210


def test_output_keys_structure():
    result = estimate_timing(["a"])
    assert set(result[0].keys()) == {"phoneme", "start_ms", "end_ms"}


def test_unknown_phoneme_uses_default_duration():
    default = PHONEME_DURATION_MS["default"]
    result = estimate_timing(["unknown1", "unknown2"])
    assert result[0]["end_ms"] == default
    assert result[1]["start_ms"] == default
    assert result[1]["end_ms"] == default * 2


def test_mixed_known_unknown():
    default = PHONEME_DURATION_MS["default"]
    result = estimate_timing(["a", "xyz"])  # 120 + default
    assert result[0]["end_ms"] == 120
    assert result[1]["start_ms"] == 120
    assert result[1]["end_ms"] == 120 + default


# ─────────────────────────────────────────────────────────────────────────────
# Extended tests — _check_espeak, get_phonemes_espeak, get_phonemes_piper,
# generate_wav_espeak, generate_wav_pyttsx3, export_phonemes, main()
# ─────────────────────────────────────────────────────────────────────────────

import subprocess  # noqa: E402
import sys  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402

import scripts.tts_phoneme_export as pe  # noqa: E402


# ── _check_espeak ─────────────────────────────────────────────────────────────

def test_check_espeak_true(monkeypatch):
    monkeypatch.setattr(pe.subprocess, "run", MagicMock(return_value=MagicMock()))
    assert pe._check_espeak() is True


def test_check_espeak_false_file_not_found(monkeypatch):
    monkeypatch.setattr(pe.subprocess, "run", MagicMock(side_effect=FileNotFoundError))
    assert pe._check_espeak() is False


def test_check_espeak_false_called_process_error(monkeypatch):
    monkeypatch.setattr(
        pe.subprocess, "run",
        MagicMock(side_effect=subprocess.CalledProcessError(1, "espeak-ng"))
    )
    assert pe._check_espeak() is False


# ── get_phonemes_espeak ───────────────────────────────────────────────────────

def test_get_phonemes_espeak_known_vowel(monkeypatch):
    mock_run = MagicMock()
    mock_run.return_value.stdout = "a e i\n"
    monkeypatch.setattr(pe.subprocess, "run", mock_run)
    result = pe.get_phonemes_espeak("hello")
    assert result == ["a", "e", "i"]


def test_get_phonemes_espeak_strips_stress_marks(monkeypatch):
    mock_run = MagicMock()
    mock_run.return_value.stdout = "ˈa\n"  # stress mark + vowel
    monkeypatch.setattr(pe.subprocess, "run", mock_run)
    result = pe.get_phonemes_espeak("stress")
    assert "a" in result


def test_get_phonemes_espeak_unknown_alpha_becomes_default(monkeypatch):
    mock_run = MagicMock()
    mock_run.return_value.stdout = "p\n"  # consonant not in dict
    monkeypatch.setattr(pe.subprocess, "run", mock_run)
    result = pe.get_phonemes_espeak("pee")
    assert result == ["default"]


def test_get_phonemes_espeak_empty_output(monkeypatch):
    mock_run = MagicMock()
    mock_run.return_value.stdout = ""
    monkeypatch.setattr(pe.subprocess, "run", mock_run)
    assert pe.get_phonemes_espeak("") == []


def test_get_phonemes_espeak_subprocess_error_returns_empty(monkeypatch):
    monkeypatch.setattr(
        pe.subprocess, "run",
        MagicMock(side_effect=subprocess.CalledProcessError(1, "espeak-ng"))
    )
    assert pe.get_phonemes_espeak("fail") == []


def test_get_phonemes_espeak_file_not_found_returns_empty(monkeypatch):
    monkeypatch.setattr(pe.subprocess, "run", MagicMock(side_effect=FileNotFoundError))
    assert pe.get_phonemes_espeak("fail") == []


def test_get_phonemes_espeak_skips_whitespace_and_boundary(monkeypatch):
    mock_run = MagicMock()
    mock_run.return_value.stdout = "a _ | b\n"  # _ and | are boundary markers
    monkeypatch.setattr(pe.subprocess, "run", mock_run)
    result = pe.get_phonemes_espeak("test")
    # _ and | skipped; 'a' → vowel; 'b' → consonant → default
    assert "a" in result
    assert "default" in result
    assert "_" not in result
    assert "|" not in result


# ── get_phonemes_piper ────────────────────────────────────────────────────────

def test_get_phonemes_piper_model_missing(monkeypatch, tmp_path):
    mock_piper = MagicMock()
    with patch.dict(sys.modules, {"piper": mock_piper}):
        with patch.object(pe.Path, "home", return_value=tmp_path):
            result = pe.get_phonemes_piper("hello")
    # Model doesn't exist in tmp_path → returns []
    assert result == []


def test_get_phonemes_piper_returns_phonemes(monkeypatch, tmp_path):
    # Create fake model files
    voices = tmp_path / ".local" / "share" / "piper" / "voices"
    voices.mkdir(parents=True)
    (voices / "en_US-amy-medium.onnx").touch()
    (voices / "en_US-amy-medium.onnx.json").touch()

    mock_voice = MagicMock()
    mock_voice.phonemize.return_value = [["a", "ˈ", "i", " ", "o"]]

    mock_piper = MagicMock()
    mock_piper.PiperVoice.load.return_value = mock_voice

    with patch.dict(sys.modules, {"piper": mock_piper}):
        with patch.object(pe.Path, "home", return_value=tmp_path):
            result = pe.get_phonemes_piper("aio")

    assert "a" in result
    assert "i" in result
    assert "o" in result


def test_get_phonemes_piper_exception_returns_empty():
    with patch.dict(sys.modules, {"piper": None}):
        result = pe.get_phonemes_piper("fail")
    assert result == []


def test_get_phonemes_piper_isalpha_non_dict_phoneme(monkeypatch, tmp_path):
    """Lines 90-91: phonema alfa non in PHONEME_DURATION_MS → 'default'."""
    voices = tmp_path / ".local" / "share" / "piper" / "voices"
    voices.mkdir(parents=True)
    (voices / "en_US-amy-medium.onnx").touch()
    (voices / "en_US-amy-medium.onnx.json").touch()

    mock_voice = MagicMock()
    mock_voice.phonemize.return_value = [["p"]]  # 'p' not in PHONEME_DURATION_MS

    mock_piper = MagicMock()
    mock_piper.PiperVoice.load.return_value = mock_voice

    with patch.dict(sys.modules, {"piper": mock_piper}):
        with patch.object(pe.Path, "home", return_value=tmp_path):
            result = pe.get_phonemes_piper("pee")

    assert result == ["default"]


def test_get_phonemes_espeak_stripped_empty_skipped(monkeypatch):
    """Line 126: char ridotto a '' da _STRIP_RE → continue (branch not-stripped)."""
    # IPA stress mark ˈ (U+02C8) viene rimosso da _STRIP_RE → stripped=""
    mock_run = MagicMock()
    mock_run.return_value.stdout = "ˈ"   # solo stress mark → stripped=""
    monkeypatch.setattr(pe.subprocess, "run", mock_run)
    result = pe.get_phonemes_espeak("stress")
    assert result == []


# ── generate_wav_espeak ───────────────────────────────────────────────────────

def test_generate_wav_espeak_success(monkeypatch):
    monkeypatch.setattr(pe.subprocess, "run", MagicMock())
    assert pe.generate_wav_espeak("hello", "/tmp/test.wav") is True


def test_generate_wav_espeak_failure(monkeypatch):
    monkeypatch.setattr(
        pe.subprocess, "run",
        MagicMock(side_effect=FileNotFoundError)
    )
    assert pe.generate_wav_espeak("hello", "/tmp/test.wav") is False


def test_generate_wav_espeak_called_process_error(monkeypatch):
    monkeypatch.setattr(
        pe.subprocess, "run",
        MagicMock(side_effect=subprocess.CalledProcessError(1, "espeak-ng"))
    )
    assert pe.generate_wav_espeak("hello", "/tmp/test.wav") is False


# ── generate_wav_pyttsx3 ──────────────────────────────────────────────────────

def test_generate_wav_pyttsx3_success():
    mock_engine = MagicMock()
    mock_pyttsx3 = MagicMock()
    mock_pyttsx3.init.return_value = mock_engine
    with patch.dict(sys.modules, {"pyttsx3": mock_pyttsx3}):
        result = pe.generate_wav_pyttsx3("hello", "/tmp/test.wav")
    assert result is True
    mock_engine.save_to_file.assert_called_once_with("hello", "/tmp/test.wav")
    mock_engine.runAndWait.assert_called_once()


def test_generate_wav_pyttsx3_exception_returns_false():
    with patch.dict(sys.modules, {"pyttsx3": None}):
        result = pe.generate_wav_pyttsx3("fail", "/tmp/fail.wav")
    assert result is False


# ── export_phonemes ───────────────────────────────────────────────────────────

def test_export_phonemes_espeak_available(monkeypatch, tmp_path):
    monkeypatch.setattr(pe, "_check_espeak", MagicMock(return_value=True))
    monkeypatch.setattr(pe, "get_phonemes_espeak", MagicMock(return_value=["a", "i"]))
    monkeypatch.setattr(pe, "generate_wav_espeak", MagicMock(return_value=True))
    # Create a fake WAV file
    wav_path = tmp_path / "tts_output.wav"
    wav_path.write_bytes(b"FAKEWAV")
    result = pe.export_phonemes("hello", str(tmp_path))
    assert result["text"] == "hello"
    assert len(result["phonemes"]) == 2
    assert result["wav_b64"] is not None


def test_export_phonemes_espeak_unavailable_uses_piper(monkeypatch, tmp_path):
    monkeypatch.setattr(pe, "_check_espeak", MagicMock(return_value=False))
    monkeypatch.setattr(pe, "get_phonemes_piper", MagicMock(return_value=["o"]))
    monkeypatch.setattr(pe, "generate_wav_pyttsx3", MagicMock(return_value=False))
    result = pe.export_phonemes("world", str(tmp_path))
    assert result["text"] == "world"
    assert len(result["phonemes"]) == 1
    assert result["wav_b64"] is None  # WAV generation failed


def test_export_phonemes_wav_not_generated(monkeypatch, tmp_path):
    monkeypatch.setattr(pe, "_check_espeak", MagicMock(return_value=True))
    monkeypatch.setattr(pe, "get_phonemes_espeak", MagicMock(return_value=[]))
    monkeypatch.setattr(pe, "generate_wav_espeak", MagicMock(return_value=False))
    monkeypatch.setattr(pe, "generate_wav_pyttsx3", MagicMock(return_value=False))
    result = pe.export_phonemes("test", str(tmp_path))
    assert result["wav_b64"] is None


def test_export_phonemes_espeak_wav_fails_pyttsx3_succeeds(monkeypatch, tmp_path):
    monkeypatch.setattr(pe, "_check_espeak", MagicMock(return_value=True))
    monkeypatch.setattr(pe, "get_phonemes_espeak", MagicMock(return_value=["e"]))
    monkeypatch.setattr(pe, "generate_wav_espeak", MagicMock(return_value=False))
    monkeypatch.setattr(pe, "generate_wav_pyttsx3", MagicMock(return_value=True))
    wav_path = tmp_path / "tts_output.wav"
    wav_path.write_bytes(b"WAV2")
    result = pe.export_phonemes("test", str(tmp_path))
    assert result["wav_b64"] is not None


# ── main() ────────────────────────────────────────────────────────────────────

def test_main_basic(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, "argv", ["prog", "hello world", "--output-dir", str(tmp_path)])
    monkeypatch.setattr(pe, "export_phonemes", MagicMock(return_value={
        "wav_b64": None, "phonemes": [], "text": "hello world",
    }))
    pe.main()
    out = capsys.readouterr().out
    assert "hello world" in out


def test_main_json_only(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, "argv", ["prog", "hi", "--json-only", "--output-dir", str(tmp_path)])
    monkeypatch.setattr(pe, "export_phonemes", MagicMock(return_value={
        "wav_b64": "SOMEBASE64", "phonemes": [], "text": "hi",
    }))
    pe.main()
    out = capsys.readouterr().out
    import json as _json
    result = _json.loads(out)
    assert result["wav_b64"] is None  # --json-only strips wav_b64
