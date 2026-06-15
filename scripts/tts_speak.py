#!/usr/bin/env python3
"""Quill of Calliope TTS — bilingual EN/IT code-switch + single voice fallback.

Engine priority:
  1. Piper TTS (if ONNX model in ~/.local/share/piper/voices/)
  2. pyttsx3/espeak-ng fallback (zero-setup, always available on NM)

Bilingual mode (--detect-language): splits text into sentence chunks,
detects EN vs IT per chunk via langdetect, synthesises each with the
matching espeak-ng voice, concatenates WAVs.

Operator use-case: listen to scene drafts hands-free.
Multi-voice per char: deferred indefinitely (operator-spec 2026-05-17).
"""

import argparse
import io
import logging
import os
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Optional

DEFAULT_VOICE_PYTTSX3 = "gmw/en-us"
DEFAULT_VOICE_PIPER = "en_US-amy-medium"
PIPER_MODELS_DIR = Path.home() / ".local/share/piper/voices"
DEFAULT_RATE_WPM = 175
AUDIO_PLAYER = "aplay"

# Supported bilingual voices (espeak-ng ids)
LANG_VOICE_MAP = {
    "en": "gmw/en-us",
    "it": "roa/it",
}

log = logging.getLogger(__name__)


def _piper_model_path(name: str) -> Optional[Path]:
    onnx = PIPER_MODELS_DIR / f"{name}.onnx"
    cfg = onnx.with_suffix(".onnx.json")
    return onnx if (onnx.exists() and cfg.exists()) else None


def _piper_available() -> bool:
    try:
        import piper  # noqa: F401
        return True
    except ImportError:
        return False


_pyttsx3_engine = None  # singleton — pyttsx3.init() must not be called twice per process


def _get_pyttsx3_engine(voice: str, rate_wpm: int):
    global _pyttsx3_engine
    import pyttsx3
    if _pyttsx3_engine is None:
        _pyttsx3_engine = pyttsx3.init()
    _pyttsx3_engine.setProperty("voice", voice)
    _pyttsx3_engine.setProperty("rate", rate_wpm)
    _pyttsx3_engine.setProperty("volume", 1.0)
    return _pyttsx3_engine


def _synth_pyttsx3(text: str, output_path: str, voice: str, rate_wpm: int) -> None:
    engine = _get_pyttsx3_engine(voice, rate_wpm)
    engine.save_to_file(text, output_path)
    engine.runAndWait()


def _synth_piper(text: str, output_path: str, model_path: Path) -> None:
    import wave
    from piper import PiperVoice
    voice = PiperVoice.load(
        str(model_path),
        config_path=str(model_path.with_suffix(".onnx.json")),
    )
    with wave.open(output_path, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)


def _play_wav(wav_path: str) -> None:
    try:
        subprocess.run([AUDIO_PLAYER, wav_path], check=False, capture_output=True)
    except FileNotFoundError:
        log.warning("aplay not found — cannot play audio")


def tts_speak(
    text: str,
    output_path: Optional[str] = None,
    voice: str = DEFAULT_VOICE_PYTTSX3,
    rate: float = 1.0,
    play: bool = False,
) -> bytes:
    """Synthesise text to WAV audio.

    Args:
        text: Input text.
        output_path: Save WAV here; if None uses a temp file (auto-deleted).
        voice: pyttsx3 voice ID or piper model name.
        rate: Speed multiplier (1.0 = normal).
        play: If True, play via aplay after synthesis.

    Returns:
        WAV bytes.
    """
    text = text.strip()
    if not text:
        log.warning("tts_speak: empty text")
        return b""

    keep_file = output_path is not None
    if not keep_file:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False, prefix="calliope_tts_")
        tmp.close()
        output_path = tmp.name

    try:
        piper_path = _piper_model_path(DEFAULT_VOICE_PIPER)
        if piper_path and _piper_available():
            log.info("engine=piper model=%s", piper_path.name)
            _synth_piper(text, output_path, piper_path)
        else:
            pyttsx3_voice = voice if voice.startswith("gmw/") else DEFAULT_VOICE_PYTTSX3
            rate_wpm = int(DEFAULT_RATE_WPM * rate)
            log.info("engine=pyttsx3 voice=%s rate=%d", pyttsx3_voice, rate_wpm)
            _synth_pyttsx3(text, output_path, pyttsx3_voice, rate_wpm)

        audio_bytes = Path(output_path).read_bytes()

        if play:
            _play_wav(output_path)

        return audio_bytes

    finally:
        if not keep_file:
            try:
                os.unlink(output_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Bilingual helpers
# ---------------------------------------------------------------------------

def _split_sentences(text: str) -> list:
    """Split text into sentence chunks on .!? boundaries."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _detect_lang(chunk: str, fallback: str = "en") -> str:
    """Detect language of a text chunk (EN/IT). Handles IT/PT ambiguity."""
    if len(chunk.split()) < 3:
        return fallback  # too short for reliable detection
    try:
        from langdetect import DetectorFactory, detect_langs
        DetectorFactory.seed = 42
        results = detect_langs(chunk)
        top = results[0]
        lang = top.lang
        # IT/PT ambiguity: langdetect often confuses short Italian for Portuguese
        if lang == "pt" and any(r.lang == "it" for r in results):
            it_prob = next(r.prob for r in results if r.lang == "it")
            if top.prob - it_prob < 0.25:
                lang = "it"
        return lang if lang in LANG_VOICE_MAP else fallback
    except Exception:
        return fallback


def _majority_lang(text: str) -> str:
    """Detect majority language of the whole text for fallback."""
    return _detect_lang(text, fallback="en")


def _concat_wav_chunks(wav_chunks: list) -> bytes:
    """Concatenate list of WAV bytes into a single WAV (must share params)."""
    non_empty = [b for b in wav_chunks if b]
    if not non_empty:
        return b""
    if len(non_empty) == 1:
        return non_empty[0]

    out = io.BytesIO()
    params = None
    all_frames = []
    for chunk_bytes in non_empty:
        with wave.open(io.BytesIO(chunk_bytes)) as wf:
            if params is None:
                params = wf.getparams()
            all_frames.append(wf.readframes(wf.getnframes()))

    with wave.open(out, "wb") as wout:
        wout.setparams(params)
        for frames in all_frames:
            wout.writeframes(frames)
    return out.getvalue()


def tts_speak_bilingual(
    text: str,
    output_path: Optional[str] = None,
    rate: float = 1.0,
    play: bool = False,
) -> bytes:
    """Synthesise bilingual EN/IT text with per-sentence language detection.

    Splits text into sentences, detects EN vs IT per chunk, synthesises each
    with the matching espeak-ng voice, concatenates into a single WAV.
    """
    text = text.strip()
    if not text:
        return b""

    sentences = _split_sentences(text)
    fallback_lang = _majority_lang(text)

    wav_chunks = []
    for sentence in sentences:
        lang = _detect_lang(sentence, fallback=fallback_lang)
        voice = LANG_VOICE_MAP.get(lang, LANG_VOICE_MAP["en"])
        log.debug("chunk=%r lang=%s voice=%s", sentence[:40], lang, voice)
        chunk_bytes = tts_speak(sentence, voice=voice, rate=rate, play=False)
        if chunk_bytes:
            wav_chunks.append(chunk_bytes)

    audio = _concat_wav_chunks(wav_chunks)

    if output_path:
        Path(output_path).write_bytes(audio)
    if play and audio:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False, prefix="calliope_bili_")
        tmp.close()
        try:
            Path(tmp.name).write_bytes(audio)
            _play_wav(tmp.name)
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    return audio


def main() -> None:
    parser = argparse.ArgumentParser(description="Calliope TTS — bilingual EN/IT")
    parser.add_argument("--text", help="Text to speak (or pipe via stdin)")
    parser.add_argument("--output", help="Save WAV to file (if omitted, plays immediately)")
    parser.add_argument("--voice", default=DEFAULT_VOICE_PYTTSX3)
    parser.add_argument("--rate", type=float, default=1.0, help="Speed multiplier")
    parser.add_argument("--no-play", action="store_true", help="Skip playback (write file only)")
    parser.add_argument(
        "--detect-language", action="store_true",
        help="Enable bilingual EN/IT code-switch (per-sentence lang detection)",
    )
    args = parser.parse_args()

    text = args.text or sys.stdin.read()
    if not text.strip():
        print("Error: no text", file=sys.stderr)
        sys.exit(1)

    play = not args.no_play

    if args.output:
        if args.detect_language:
            audio = tts_speak_bilingual(text, output_path=args.output, rate=args.rate, play=play)
        else:
            audio = tts_speak(text, output_path=args.output, voice=args.voice, rate=args.rate, play=play)
        print(f"Saved: {args.output} ({len(audio)/1024:.1f} KB)")
    else:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False, prefix="calliope_tts_")
        tmp.close()
        try:
            if args.detect_language:
                audio = tts_speak_bilingual(text, output_path=tmp.name, rate=args.rate, play=play)
            else:
                audio = tts_speak(text, output_path=tmp.name, voice=args.voice, rate=args.rate, play=play)
            if not play:
                print(f"Generated {len(audio)/1024:.1f} KB (not played, use --output to save)")
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass


if __name__ == "__main__":
    main()
