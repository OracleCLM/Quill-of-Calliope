"""Tests for bilingual EN/IT code-switch TTS (tts_speak_bilingual)."""
from __future__ import annotations

import io
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from tts_speak import (  # noqa: E402
    _concat_wav_chunks,
    _detect_lang,
    _majority_lang,
    _split_sentences,
    tts_speak,
    tts_speak_bilingual,
)


def _is_valid_wav(data: bytes) -> bool:
    return len(data) > 44 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"


def _wav_duration_frames(data: bytes) -> int:
    with wave.open(io.BytesIO(data)) as wf:
        return wf.getnframes()


class TestLangDetection:
    def test_en_sentence_detected(self):
        assert _detect_lang("The wind howls across the frozen peaks.") == "en"

    def test_it_sentence_detected(self):
        assert _detect_lang("Aurora alzò la mano convocando la gravità stessa.") == "it"

    def test_short_chunk_returns_fallback(self):
        # <3 words → fallback regardless
        assert _detect_lang("Ciao", fallback="en") == "en"
        assert _detect_lang("Hello", fallback="it") == "it"

    def test_majority_lang_en(self):
        text = "The blade remembers. The heart forgets. Victory comes at a price."
        assert _majority_lang(text) == "en"

    def test_majority_lang_it(self):
        text = "Aurora alzò la mano. Il vento soffiava forte. La folla rimase in silenzio."
        assert _majority_lang(text) == "it"


class TestSplitSentences:
    def test_splits_on_period(self):
        chunks = _split_sentences("Hello world. How are you?")
        assert len(chunks) == 2

    def test_handles_single_sentence(self):
        chunks = _split_sentences("Single sentence here.")
        assert len(chunks) == 1
        assert chunks[0] == "Single sentence here."

    def test_handles_mixed_punctuation(self):
        chunks = _split_sentences("Wait! Really? Yes, indeed.")
        assert len(chunks) == 3


class TestConcatWav:
    def test_concat_two_chunks(self):
        a = tts_speak("Hello world.", play=False)
        b = tts_speak("Ciao mondo.", voice="roa/it", play=False)
        combined = _concat_wav_chunks([a, b])
        assert _is_valid_wav(combined)
        # Combined should be longer than either individual chunk
        assert _wav_duration_frames(combined) > _wav_duration_frames(a)
        assert _wav_duration_frames(combined) > _wav_duration_frames(b)

    def test_concat_empty_list_returns_empty(self):
        assert _concat_wav_chunks([]) == b""

    def test_concat_single_passthrough(self):
        a = tts_speak("Just one sentence.", play=False)
        result = _concat_wav_chunks([a])
        assert result == a


class TestBilingualSpeak:
    def test_en_only_text(self, tmp_path):
        text = "The blade remembers what the heart forgets. Aurora raised her hand."
        out = str(tmp_path / "en_only.wav")
        audio = tts_speak_bilingual(text, output_path=out, play=False)
        assert _is_valid_wav(audio)
        assert Path(out).stat().st_size > 0

    def test_it_only_text(self, tmp_path):
        text = "Aurora alzò la mano convocando la gravità. Il vento soffiava forte sulle montagne."
        out = str(tmp_path / "it_only.wav")
        audio = tts_speak_bilingual(text, output_path=out, play=False)
        assert _is_valid_wav(audio)
        assert len(audio) > 10_000

    def test_mixed_en_it(self, tmp_path):
        # Explicit EN then IT sentences
        text = (
            "The wind howls across the frozen peaks. "
            "Aurora alzò la mano convocando la gravità stessa. "
            "She had trained for this her entire life."
        )
        out = str(tmp_path / "mixed.wav")
        audio = tts_speak_bilingual(text, output_path=out, play=False)
        assert _is_valid_wav(audio)
        # Mixed output should be longer than a single short sentence
        assert len(audio) > 50_000

    def test_majority_lang_fallback(self, tmp_path):
        # Very short ambiguous chunk → fallback to majority language (EN)
        text = "Hello. Ciao. The sun rises over the ancient kingdom of Yokai."
        out = str(tmp_path / "fallback.wav")
        audio = tts_speak_bilingual(text, output_path=out, play=False)
        assert _is_valid_wav(audio)
        assert len(audio) > 0
