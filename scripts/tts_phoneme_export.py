#!/usr/bin/env python3
"""TTS phoneme export — thin re-export of the shared, repo-agnostic implementation.

Canonical module: ``shared/live2d_mascot/server/tts_phoneme_export.py`` (consumed by
both Calliope and Vesta). This shim keeps the historical ``scripts/`` import path and
CLI entry point working (``from tts_phoneme_export import export_phonemes`` and
``python scripts/tts_phoneme_export.py ...``).
"""
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parent.parent / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from live2d_mascot.server.tts_phoneme_export import (  # noqa: E402,F401
    MOUTH_SHAPES,
    PHONEME_DURATION_MS,
    VOWEL_PHONEMES,
    estimate_timing,
    export_phonemes,
    generate_wav_espeak,
    generate_wav_pyttsx3,
    get_phonemes_espeak,
    get_phonemes_piper,
    main,
)

if __name__ == "__main__":
    main()
