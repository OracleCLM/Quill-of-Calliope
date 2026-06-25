"""Unit test per scripts/tts_speak.py — _split_sentences e _detect_lang (pure)."""
from __future__ import annotations

from scripts.tts_speak import _detect_lang, _split_sentences


# ── _split_sentences ──────────────────────────────────────────────────────────

def test_split_three_sentences():
    result = _split_sentences("Hello world. This is a test! How are you?")
    assert result == ["Hello world.", "This is a test!", "How are you?"]


def test_split_single_sentence():
    assert _split_sentences("Single sentence.") == ["Single sentence."]


def test_split_empty_string():
    assert _split_sentences("") == []


def test_split_whitespace_only():
    assert _split_sentences("  \n  ") == []


def test_split_no_punctuation():
    assert _split_sentences("No punctuation here") == ["No punctuation here"]


def test_split_dotted_abbreviation_no_spaces():
    # "A.B.C." has no spaces after punctuation → single chunk
    assert _split_sentences("A.B.C.") == ["A.B.C."]


def test_split_strips_whitespace_from_parts():
    result = _split_sentences("First.  Second!")
    assert result == ["First.", "Second!"]


# ── _detect_lang ─────────────────────────────────────────────────────────────

def test_detect_en_long():
    assert _detect_lang("The dragon flies high above the mountain range.") == "en"


def test_detect_short_returns_fallback():
    # < 3 parole → fallback
    assert _detect_lang("Hi", fallback="en") == "en"
    assert _detect_lang("Ciao", fallback="it") == "it"


def test_detect_fallback_default_is_en():
    assert _detect_lang("Hi") == "en"


# ─────────────────────────────────────────────────────────────────────────────
# Extended tests — _piper_model_path, _piper_available, _get_pyttsx3_engine,
# _synth_pyttsx3, _synth_piper, _play_wav, tts_speak, _detect_lang branches,
# _majority_lang, _concat_wav_chunks, tts_speak_bilingual, main()
# ─────────────────────────────────────────────────────────────────────────────

import io  # noqa: E402
import sys  # noqa: E402
import wave  # noqa: E402
from pathlib import Path  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402

import pytest  # noqa: E402

from scripts import tts_speak as tts_module  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_pyttsx3_engine(monkeypatch):
    monkeypatch.setattr(tts_module, "_pyttsx3_engine", None)


# ── _piper_model_path ─────────────────────────────────────────────────────────

def test_piper_model_path_returns_onnx_when_both_exist(tmp_path):
    onnx = tmp_path / "en_US-amy-medium.onnx"
    cfg = tmp_path / "en_US-amy-medium.onnx.json"
    onnx.touch()
    cfg.touch()
    with patch.object(tts_module, "PIPER_MODELS_DIR", tmp_path):
        result = tts_module._piper_model_path("en_US-amy-medium")
    assert result == onnx


def test_piper_model_path_returns_none_when_onnx_missing(tmp_path):
    with patch.object(tts_module, "PIPER_MODELS_DIR", tmp_path):
        result = tts_module._piper_model_path("en_US-amy-medium")
    assert result is None


def test_piper_model_path_returns_none_when_json_missing(tmp_path):
    onnx = tmp_path / "en_US-amy-medium.onnx"
    onnx.touch()
    with patch.object(tts_module, "PIPER_MODELS_DIR", tmp_path):
        result = tts_module._piper_model_path("en_US-amy-medium")
    assert result is None


# ── _piper_available ──────────────────────────────────────────────────────────

def test_piper_available_true(monkeypatch):
    monkeypatch.setitem(sys.modules, "piper", MagicMock())
    assert tts_module._piper_available() is True


def test_piper_available_false():
    with patch.dict(sys.modules, {"piper": None}):
        assert tts_module._piper_available() is False


# ── _get_pyttsx3_engine ───────────────────────────────────────────────────────

def test_get_pyttsx3_engine_init_once_and_sets_properties():
    mock_engine = MagicMock()
    mock_pyttsx3 = MagicMock()
    mock_pyttsx3.init.return_value = mock_engine
    with patch.dict(sys.modules, {"pyttsx3": mock_pyttsx3}):
        e1 = tts_module._get_pyttsx3_engine("gmw/en-us", 150)
        e2 = tts_module._get_pyttsx3_engine("gmw/en-us", 200)
    assert e1 is e2
    mock_pyttsx3.init.assert_called_once()
    assert mock_engine.setProperty.call_count == 6  # 3 props × 2 calls


# ── _synth_pyttsx3 ────────────────────────────────────────────────────────────

def test_synth_pyttsx3_calls_save_and_run(monkeypatch):
    mock_engine = MagicMock()
    monkeypatch.setattr(tts_module, "_get_pyttsx3_engine", MagicMock(return_value=mock_engine))
    tts_module._synth_pyttsx3("hello", "out.wav", "gmw/en-us", 150)
    mock_engine.save_to_file.assert_called_once_with("hello", "out.wav")
    mock_engine.runAndWait.assert_called_once()


# ── _synth_piper ──────────────────────────────────────────────────────────────

def test_synth_piper_loads_and_synthesizes():
    mock_voice = MagicMock()
    mock_piper_mod = MagicMock()
    mock_piper_mod.PiperVoice.load.return_value = mock_voice
    mock_wav_file = MagicMock()
    mock_wave_ctx = MagicMock()
    mock_wave_ctx.__enter__ = MagicMock(return_value=mock_wav_file)
    mock_wave_ctx.__exit__ = MagicMock(return_value=False)

    with patch.dict(sys.modules, {"piper": mock_piper_mod}):
        with patch("scripts.tts_speak.wave.open", return_value=mock_wave_ctx):
            tts_module._synth_piper("hello", "out.wav", Path("model.onnx"))

    mock_piper_mod.PiperVoice.load.assert_called_once()
    mock_voice.synthesize_wav.assert_called_once_with("hello", mock_wav_file)


# ── _play_wav ─────────────────────────────────────────────────────────────────

def test_play_wav_calls_subprocess(monkeypatch):
    mock_run = MagicMock()
    monkeypatch.setattr(tts_module.subprocess, "run", mock_run)
    tts_module._play_wav("test.wav")
    mock_run.assert_called_once_with(
        [tts_module.AUDIO_PLAYER, "test.wav"], check=False, capture_output=True
    )


def test_play_wav_not_found_logs_warning(monkeypatch):
    monkeypatch.setattr(
        tts_module.subprocess, "run", MagicMock(side_effect=FileNotFoundError)
    )
    with patch.object(tts_module.log, "warning") as mock_warn:
        tts_module._play_wav("test.wav")
    mock_warn.assert_called_once()


# ── tts_speak ─────────────────────────────────────────────────────────────────

def test_tts_speak_empty_text_returns_empty():
    assert tts_module.tts_speak("   ") == b""


def test_tts_speak_uses_piper_when_available(tmp_path, monkeypatch):
    out = tmp_path / "out.wav"
    monkeypatch.setattr(tts_module, "_piper_model_path", MagicMock(return_value=Path("model.onnx")))
    monkeypatch.setattr(tts_module, "_piper_available", MagicMock(return_value=True))
    mock_synth = MagicMock()
    monkeypatch.setattr(tts_module, "_synth_piper", mock_synth)
    with patch.object(Path, "read_bytes", return_value=b"WAVDATA"):
        result = tts_module.tts_speak("hello", output_path=str(out))
    assert result == b"WAVDATA"
    mock_synth.assert_called_once()


def test_tts_speak_uses_pyttsx3_when_no_piper(monkeypatch):
    monkeypatch.setattr(tts_module, "_piper_model_path", MagicMock(return_value=None))
    mock_synth = MagicMock()
    monkeypatch.setattr(tts_module, "_synth_pyttsx3", mock_synth)
    with patch.object(Path, "read_bytes", return_value=b"WAVDATA"):
        result = tts_module.tts_speak("hello", output_path="/dev/null")
    assert result == b"WAVDATA"
    mock_synth.assert_called_once()


def test_tts_speak_non_gmw_voice_uses_default(monkeypatch):
    monkeypatch.setattr(tts_module, "_piper_model_path", MagicMock(return_value=None))
    mock_synth = MagicMock()
    monkeypatch.setattr(tts_module, "_synth_pyttsx3", mock_synth)
    with patch.object(Path, "read_bytes", return_value=b"WAV"):
        tts_module.tts_speak("hello", output_path="/dev/null", voice="custom/voice")
    call_args = mock_synth.call_args[0]
    assert call_args[2] == tts_module.DEFAULT_VOICE_PYTTSX3


def test_tts_speak_temp_file_cleaned_up(monkeypatch):
    mock_tmp = MagicMock()
    mock_tmp.name = "/tmp/calliope_tts_test.wav"
    monkeypatch.setattr(
        tts_module.tempfile, "NamedTemporaryFile", MagicMock(return_value=mock_tmp)
    )
    monkeypatch.setattr(tts_module, "_piper_model_path", MagicMock(return_value=None))
    monkeypatch.setattr(tts_module, "_synth_pyttsx3", MagicMock())
    mock_unlink = MagicMock()
    monkeypatch.setattr(tts_module.os, "unlink", mock_unlink)
    with patch.object(Path, "read_bytes", return_value=b"WAV"):
        tts_module.tts_speak("hello")
    mock_unlink.assert_called_once_with("/tmp/calliope_tts_test.wav")


def test_tts_speak_play_calls_play_wav(monkeypatch):
    monkeypatch.setattr(tts_module, "_piper_model_path", MagicMock(return_value=None))
    monkeypatch.setattr(tts_module, "_synth_pyttsx3", MagicMock())
    mock_play = MagicMock()
    monkeypatch.setattr(tts_module, "_play_wav", mock_play)
    with patch.object(Path, "read_bytes", return_value=b"WAV"):
        tts_module.tts_speak("hello", output_path="/dev/null", play=True)
    mock_play.assert_called_once()


# ── _detect_lang (additional branches) ───────────────────────────────────────

def test_detect_lang_pt_it_ambiguity_resolves_to_it():
    mock_res_pt = MagicMock(lang="pt", prob=0.6)
    mock_res_it = MagicMock(lang="it", prob=0.45)
    mock_langdetect = MagicMock()
    mock_langdetect.DetectorFactory = MagicMock()
    mock_langdetect.detect_langs.return_value = [mock_res_pt, mock_res_it]
    with patch.dict(sys.modules, {"langdetect": mock_langdetect}):
        result = tts_module._detect_lang("questo testo è abbastanza lungo per rilevare la lingua")
    assert result == "it"


def test_detect_lang_exception_returns_fallback():
    mock_langdetect = MagicMock()
    mock_langdetect.DetectorFactory = MagicMock()
    mock_langdetect.detect_langs.side_effect = Exception("fail")
    with patch.dict(sys.modules, {"langdetect": mock_langdetect}):
        result = tts_module._detect_lang("some text long enough", fallback="it")
    assert result == "it"


def test_detect_lang_unknown_lang_returns_fallback():
    mock_res = MagicMock(lang="zh", prob=0.99)
    mock_langdetect = MagicMock()
    mock_langdetect.DetectorFactory = MagicMock()
    mock_langdetect.detect_langs.return_value = [mock_res]
    with patch.dict(sys.modules, {"langdetect": mock_langdetect}):
        result = tts_module._detect_lang("some unknown language text here", fallback="en")
    assert result == "en"


# ── _majority_lang ────────────────────────────────────────────────────────────

def test_majority_lang_delegates_to_detect_lang(monkeypatch):
    monkeypatch.setattr(tts_module, "_detect_lang", MagicMock(return_value="it"))
    assert tts_module._majority_lang("qualsiasi testo") == "it"


# ── _concat_wav_chunks ────────────────────────────────────────────────────────

def _make_wav_bytes(n_frames: int = 50) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(22050)
        wf.writeframes(b"\x00" * (n_frames * 2))
    return buf.getvalue()


def test_concat_wav_chunks_empty_list():
    assert tts_module._concat_wav_chunks([]) == b""


def test_concat_wav_chunks_empty_bytes_filtered():
    assert tts_module._concat_wav_chunks([b"", b""]) == b""


def test_concat_wav_chunks_single_chunk():
    wav = _make_wav_bytes(50)
    assert tts_module._concat_wav_chunks([wav]) == wav


def test_concat_wav_chunks_multiple_produces_valid_wav():
    chunk1 = _make_wav_bytes(50)
    chunk2 = _make_wav_bytes(50)
    result = tts_module._concat_wav_chunks([chunk1, chunk2])
    with wave.open(io.BytesIO(result)) as wf:
        assert wf.getnframes() == 100  # 50 + 50 frames


# ── tts_speak_bilingual ───────────────────────────────────────────────────────

def test_tts_speak_bilingual_empty_returns_empty():
    assert tts_module.tts_speak_bilingual("   ") == b""


def test_tts_speak_bilingual_combines_chunks(monkeypatch):
    monkeypatch.setattr(tts_module, "_split_sentences", MagicMock(return_value=["A.", "B."]))
    monkeypatch.setattr(tts_module, "_majority_lang", MagicMock(return_value="en"))
    monkeypatch.setattr(tts_module, "_detect_lang", MagicMock(side_effect=["en", "it"]))
    monkeypatch.setattr(tts_module, "tts_speak", MagicMock(side_effect=[b"WAV1", b"WAV2"]))
    monkeypatch.setattr(tts_module, "_concat_wav_chunks", MagicMock(return_value=b"COMBINED"))
    result = tts_module.tts_speak_bilingual("A. B.")
    assert result == b"COMBINED"


def test_tts_speak_bilingual_saves_to_output_path(monkeypatch, tmp_path):
    out = tmp_path / "output.wav"
    monkeypatch.setattr(tts_module, "_split_sentences", MagicMock(return_value=["Hello."]))
    monkeypatch.setattr(tts_module, "_majority_lang", MagicMock(return_value="en"))
    monkeypatch.setattr(tts_module, "_detect_lang", MagicMock(return_value="en"))
    monkeypatch.setattr(tts_module, "tts_speak", MagicMock(return_value=b"WAVDATA"))
    monkeypatch.setattr(tts_module, "_concat_wav_chunks", MagicMock(return_value=b"WAVDATA"))
    tts_module.tts_speak_bilingual("Hello.", output_path=str(out))
    assert out.read_bytes() == b"WAVDATA"


def test_tts_speak_bilingual_play(monkeypatch):
    monkeypatch.setattr(tts_module, "_split_sentences", MagicMock(return_value=["Hi."]))
    monkeypatch.setattr(tts_module, "_majority_lang", MagicMock(return_value="en"))
    monkeypatch.setattr(tts_module, "_detect_lang", MagicMock(return_value="en"))
    monkeypatch.setattr(tts_module, "tts_speak", MagicMock(return_value=b"WAV"))
    monkeypatch.setattr(tts_module, "_concat_wav_chunks", MagicMock(return_value=b"WAV"))
    mock_play = MagicMock()
    monkeypatch.setattr(tts_module, "_play_wav", mock_play)
    mock_tmp = MagicMock()
    mock_tmp.name = "/tmp/bili_test.wav"
    monkeypatch.setattr(tts_module.tempfile, "NamedTemporaryFile", MagicMock(return_value=mock_tmp))
    monkeypatch.setattr(tts_module.os, "unlink", MagicMock())
    with patch.object(Path, "write_bytes", MagicMock()):
        tts_module.tts_speak_bilingual("Hi.", play=True)
    mock_play.assert_called_once_with("/tmp/bili_test.wav")


def test_tts_speak_bilingual_unlink_oserror_silenced(monkeypatch):
    """Lines 250-251: OSError in unlink durante finally di tts_speak_bilingual → silenziata."""
    monkeypatch.setattr(tts_module, "_split_sentences", MagicMock(return_value=["Hi."]))
    monkeypatch.setattr(tts_module, "_majority_lang", MagicMock(return_value="en"))
    monkeypatch.setattr(tts_module, "_detect_lang", MagicMock(return_value="en"))
    monkeypatch.setattr(tts_module, "tts_speak", MagicMock(return_value=b"WAV"))
    monkeypatch.setattr(tts_module, "_concat_wav_chunks", MagicMock(return_value=b"WAV"))
    mock_play = MagicMock()
    monkeypatch.setattr(tts_module, "_play_wav", mock_play)
    mock_tmp = MagicMock()
    mock_tmp.name = "/tmp/bili_oserr.wav"
    monkeypatch.setattr(tts_module.tempfile, "NamedTemporaryFile", MagicMock(return_value=mock_tmp))
    monkeypatch.setattr(tts_module.os, "unlink", MagicMock(side_effect=OSError("busy")))
    with patch.object(Path, "write_bytes", MagicMock()):
        tts_module.tts_speak_bilingual("Hi.", play=True)  # non deve sollevare
    mock_play.assert_called_once()


# ── main() ────────────────────────────────────────────────────────────────────

def test_main_text_with_output(monkeypatch, capsys, tmp_path):
    out = tmp_path / "out.wav"
    monkeypatch.setattr(sys, "argv", ["prog", "--text", "Hello world", "--output", str(out)])
    monkeypatch.setattr(tts_module, "tts_speak", MagicMock(return_value=b"WAVDATA"))
    tts_module.main()
    assert "Saved:" in capsys.readouterr().out


def test_main_empty_text_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--text", "   "])
    with pytest.raises(SystemExit) as exc:
        tts_module.main()
    assert exc.value.code == 1


def test_main_stdin_no_play_no_output(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["prog", "--no-play"])
    monkeypatch.setattr(sys, "stdin", MagicMock(read=MagicMock(return_value="Hello world")))
    mock_tmp = MagicMock()
    mock_tmp.name = "/tmp/calliope_tts_stdin.wav"
    monkeypatch.setattr(tts_module.tempfile, "NamedTemporaryFile", MagicMock(return_value=mock_tmp))
    monkeypatch.setattr(tts_module, "tts_speak", MagicMock(return_value=b"WAV"))
    monkeypatch.setattr(tts_module.os, "unlink", MagicMock())
    tts_module.main()
    assert "Generated" in capsys.readouterr().out


def test_main_detect_language_with_output(monkeypatch, capsys, tmp_path):
    out = tmp_path / "bili.wav"
    monkeypatch.setattr(sys, "argv", [
        "prog", "--text", "Hello world", "--output", str(out), "--detect-language",
    ])
    monkeypatch.setattr(tts_module, "tts_speak_bilingual", MagicMock(return_value=b"WAV"))
    tts_module.main()
    assert "Saved:" in capsys.readouterr().out


def test_main_detect_language_no_output(monkeypatch, capsys):
    """Line 287: detect_language + no-play + no-output → bilingual via tmp file."""
    monkeypatch.setattr(sys, "argv", ["prog", "--text", "Ciao mondo", "--no-play", "--detect-language"])
    mock_tmp = MagicMock()
    mock_tmp.name = "/tmp/calliope_tts_bili.wav"
    monkeypatch.setattr(tts_module.tempfile, "NamedTemporaryFile", MagicMock(return_value=mock_tmp))
    monkeypatch.setattr(tts_module, "tts_speak_bilingual", MagicMock(return_value=b"WAV"))
    monkeypatch.setattr(tts_module.os, "unlink", MagicMock())
    tts_module.main()
    out = capsys.readouterr().out
    assert "Generated" in out


def test_main_no_output_unlink_oserror_silenced(monkeypatch):
    """Lines 295-296: OSError in unlink durante cleanup main → silenziosamente ignorata."""
    monkeypatch.setattr(sys, "argv", ["prog", "--text", "Hello", "--no-play"])
    mock_tmp = MagicMock()
    mock_tmp.name = "/tmp/calliope_tts_oserr.wav"
    monkeypatch.setattr(tts_module.tempfile, "NamedTemporaryFile", MagicMock(return_value=mock_tmp))
    monkeypatch.setattr(tts_module, "tts_speak", MagicMock(return_value=b"WAV"))
    monkeypatch.setattr(tts_module.os, "unlink", MagicMock(side_effect=OSError("busy")))
    tts_module.main()  # non deve sollevare


def test_tts_speak_unlink_oserror_silenced(monkeypatch):
    """Lines 147-148: OSError in unlink durante cleanup tts_speak → silenziata."""
    mock_tmp = MagicMock()
    mock_tmp.name = "/tmp/calliope_tts_speak_oserr.wav"
    monkeypatch.setattr(tts_module.tempfile, "NamedTemporaryFile", MagicMock(return_value=mock_tmp))
    monkeypatch.setattr(tts_module, "_piper_model_path", MagicMock(return_value=None))
    monkeypatch.setattr(tts_module, "_synth_pyttsx3", MagicMock())
    monkeypatch.setattr(tts_module.os, "unlink", MagicMock(side_effect=OSError("busy")))
    with patch.object(Path, "read_bytes", return_value=b"WAV"):
        tts_module.tts_speak("hello")  # non deve sollevare
