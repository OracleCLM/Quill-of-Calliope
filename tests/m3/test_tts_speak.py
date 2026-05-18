"""Tests for scripts/tts_speak.py — audio generation (no playback)."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from tts_speak import tts_speak  # noqa: E402


def _is_valid_wav(data: bytes) -> bool:
    """Minimal RIFF/WAVE header check."""
    return len(data) > 44 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"


class TestTtsSpeak:
    def test_short_text_generates_wav(self, tmp_path):
        out = str(tmp_path / "short.wav")
        audio = tts_speak("The blade remembers what the heart forgets.", output_path=out, play=False)
        assert len(audio) > 0, "audio bytes empty"
        assert _is_valid_wav(audio), "not a valid WAV"
        assert Path(out).exists()
        assert Path(out).stat().st_size > 0

    def test_long_paragraph_generates_wav(self, tmp_path):
        text = (
            "Aurora raised her hand, summoning gravity itself. "
            "The crowd fell silent as the air shimmered and bent. "
            "Ancient forces older than the Kingdom stirred beneath her fingertips. "
            "She had trained for this moment her entire life, yet nothing could have prepared her "
            "for the weight of three hundred souls watching, waiting, hoping. "
            "The ground trembled. The sky darkened. And then — stillness."
        )
        assert len(text.split()) > 60, "test text not long enough"
        out = str(tmp_path / "long.wav")
        audio = tts_speak(text, output_path=out, play=False)
        assert len(audio) > 10_000, f"audio too small: {len(audio)} bytes"
        assert _is_valid_wav(audio)

    def test_special_chars_generates_wav(self, tmp_path):
        text = "It's 3 o'clock. The café is empty — isn't it? 42 guards: none remain."
        out = str(tmp_path / "special.wav")
        audio = tts_speak(text, output_path=out, play=False)
        assert len(audio) > 0
        assert _is_valid_wav(audio)

    def test_empty_text_returns_empty_bytes(self, tmp_path):
        out = str(tmp_path / "empty.wav")
        audio = tts_speak("   ", output_path=out, play=False)
        assert audio == b""

    def test_rate_multiplier_accepted(self, tmp_path):
        out = str(tmp_path / "fast.wav")
        audio = tts_speak("Quick brown fox.", output_path=out, rate=1.5, play=False)
        assert _is_valid_wav(audio)

    def test_no_output_path_returns_bytes(self):
        # No output_path: internal temp file, auto-deleted
        audio = tts_speak("Hello Calliope.", play=False)
        assert _is_valid_wav(audio)

    def test_wav_sample_rate_reasonable(self, tmp_path):
        out = str(tmp_path / "rate_check.wav")
        audio = tts_speak("Check sample rate.", output_path=out, play=False)
        # WAV fmt chunk: sample rate at bytes 24-27 (little-endian uint32)
        sample_rate = struct.unpack_from("<I", audio, 24)[0]
        assert sample_rate in (8000, 16000, 22050, 24000, 44100, 48000), \
            f"unexpected sample rate: {sample_rate}"
