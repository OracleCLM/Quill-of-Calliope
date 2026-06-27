#!/usr/bin/env python3
"""TTS phoneme export — thin re-export of the shared, repo-agnostic implementation.

Canonical module: ``shared/live2d_mascot/server/tts_phoneme_export.py`` (consumed by
both Calliope and Vesta). This shim keeps the historical ``scripts/`` import path and
CLI entry point working (``from tts_phoneme_export import export_phonemes`` and
``python scripts/tts_phoneme_export.py ...``).

export_phonemes and main are overridden here to call helpers via module-level
attribute lookups, which allows monkeypatching in unit tests.
"""
import argparse
import base64
import json
import subprocess  # noqa: F401 — exposed for monkeypatching in tests
import sys
from pathlib import Path
from typing import Any, Optional

_SHARED = Path(__file__).resolve().parent.parent / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from live2d_mascot.server.tts_phoneme_export import (  # noqa: E402,F401
    MOUTH_SHAPES,
    PHONEME_DURATION_MS,
    VOWEL_PHONEMES,
    _check_espeak,
    estimate_timing,
    generate_wav_espeak,
    generate_wav_pyttsx3,
    get_phonemes_espeak,
    get_phonemes_piper,
)


def export_phonemes(text: str, output_dir: str = "/tmp") -> dict[str, Any]:
    """Re-implementation that calls helpers via module attributes (monkeypatchable)."""
    _self = sys.modules[__name__]
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    wav_path = out_dir / "tts_output.wav"

    espeak_ok = _self._check_espeak()
    phonemes = _self.get_phonemes_espeak(text) if espeak_ok else _self.get_phonemes_piper(text)
    timings = _self.estimate_timing(phonemes)

    wav_b64: Optional[str] = None
    generated = False
    if espeak_ok:
        generated = _self.generate_wav_espeak(text, str(wav_path))
    if not generated:
        generated = _self.generate_wav_pyttsx3(text, str(wav_path))
    if generated and wav_path.exists():
        wav_b64 = base64.b64encode(wav_path.read_bytes()).decode("utf-8")

    return {"wav_b64": wav_b64, "phonemes": timings, "text": text}


def main() -> None:
    _self = sys.modules[__name__]
    parser = argparse.ArgumentParser(
        description="Quill of Calliope — TTS phoneme export (espeak-ng + timing JSON)"
    )
    parser.add_argument("text", help="Input text to synthesise")
    parser.add_argument("--output-dir", default="/tmp", help="Directory for temp WAV")
    parser.add_argument("--json-only", action="store_true", help="Omit wav_b64 from output")
    args = parser.parse_args()

    result = _self.export_phonemes(args.text, args.output_dir)  # type: ignore[attr-defined]
    if args.json_only:
        result["wav_b64"] = None

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
