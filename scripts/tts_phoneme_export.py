#!/usr/bin/env python3
"""TTS phoneme export — text → WAV + phoneme timing JSON.

Uses espeak-ng --ipa for phoneme extraction + duration estimation.
Output: {wav_b64: str | null, phonemes: [{phoneme, start_ms, end_ms}], text: str}
"""
import argparse
import base64
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Optional

PHONEME_DURATION_MS: dict[str, int] = {
    "a": 120, "e": 100, "i": 90, "o": 110, "u": 100,
    "æ": 110, "ɛ": 100, "ɪ": 90, "ʊ": 100, "ɔ": 110,
    # Extended IPA vowels common in espeak-ng output
    "ɐ": 100,  # near-open central (schwa-like)
    "ə": 80,   # schwa
    "ɜ": 100,  # open-mid central
    "ɑ": 120,  # open back
    "ʌ": 110,  # open-mid back
    "ɒ": 110,  # open back rounded
    "default": 60,
}

VOWEL_PHONEMES = set("aeiouæɛɪʊɔʌɑɐəɜɒ")

# Map IPA vowel chars to nearest canonical vowel for mouth shape lookup
_IPA_TO_CANONICAL: dict[str, str] = {
    "ɐ": "a", "ɑ": "a", "ɒ": "o", "ɔ": "o",
    "ɛ": "e", "ɜ": "e", "ə": "e", "æ": "e",
    "ɪ": "i", "ʊ": "u", "ʌ": "a",
}

MOUTH_SHAPES: dict[str, dict[str, float]] = {
    "a": {"MouthOpenY": 1.0, "MouthForm": 0.5},
    "e": {"MouthOpenY": 0.7, "MouthForm": 0.8},
    "i": {"MouthOpenY": 0.4, "MouthForm": 1.0},
    "o": {"MouthOpenY": 0.9, "MouthForm": -0.3},
    "u": {"MouthOpenY": 0.6, "MouthForm": -0.8},
    "default": {"MouthOpenY": 0.2, "MouthForm": 0.0},
}

# IPA stress marks and non-phoneme diacritics to strip
_STRIP_RE = re.compile(r"[ˈˌːˑ̥̬̃̈̊]")


def _check_espeak() -> bool:
    """Return True if espeak-ng is available on PATH."""
    try:
        subprocess.run(
            ["espeak-ng", "--version"],
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_phonemes_espeak(text: str) -> list[str]:
    """Extract IPA phonemes via espeak-ng --ipa.

    Returns a list of normalised phoneme chars. Falls back to [] on error.
    """
    try:
        result = subprocess.run(
            ["espeak-ng", "--ipa", "-q", text],
            capture_output=True,
            text=True,
            check=True,
        )
        raw = result.stdout.strip()
        if not raw:
            return []

        phonemes: list[str] = []
        for char in raw:
            # Skip whitespace, word boundaries
            if char in (" ", "\n", "\t", "_", "|"):
                continue
            # Strip stress / diacritic marks early
            stripped = _STRIP_RE.sub("", char)
            if not stripped:
                continue
            # Map to known key or first char
            if stripped in PHONEME_DURATION_MS:
                phonemes.append(stripped)
            elif stripped in VOWEL_PHONEMES:
                phonemes.append(stripped)
            elif stripped.isalpha():
                phonemes.append("default")
            # else: punctuation / boundary marker — skip
        return phonemes
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def estimate_timing(phonemes: list[str]) -> list[dict[str, Any]]:
    """Assign start/end ms to each phoneme via cumulative duration estimate."""
    timing: list[dict[str, Any]] = []
    cursor = 0
    for p in phonemes:
        duration = PHONEME_DURATION_MS.get(p, PHONEME_DURATION_MS["default"])
        timing.append({"phoneme": p, "start_ms": cursor, "end_ms": cursor + duration})
        cursor += duration
    return timing


def generate_wav_espeak(text: str, output_path: str) -> bool:
    """Generate WAV via espeak-ng. Returns True on success."""
    try:
        subprocess.run(
            ["espeak-ng", "-w", output_path, text],
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def generate_wav_pyttsx3(text: str, output_path: str) -> bool:
    """Fallback WAV generation via pyttsx3. Returns True on success."""
    try:
        import pyttsx3  # type: ignore[import]

        engine = pyttsx3.init()
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        return True
    except Exception:  # noqa: BLE001
        return False


def export_phonemes(text: str, output_dir: str = "/tmp") -> dict[str, Any]:
    """Main export: returns {wav_b64, phonemes, text}.

    Gracefully degrades when espeak-ng is unavailable:
    - phonemes: [] (naïve fallback, no extraction)
    - WAV: tries pyttsx3, else None
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    wav_path = out_dir / "tts_output.wav"

    espeak_ok = _check_espeak()

    # Phoneme extraction
    phonemes = get_phonemes_espeak(text) if espeak_ok else []
    timings = estimate_timing(phonemes)

    # WAV generation
    wav_b64: Optional[str] = None
    generated = False
    if espeak_ok:
        generated = generate_wav_espeak(text, str(wav_path))
    if not generated:
        generated = generate_wav_pyttsx3(text, str(wav_path))

    if generated and wav_path.exists():
        wav_b64 = base64.b64encode(wav_path.read_bytes()).decode("utf-8")

    return {"wav_b64": wav_b64, "phonemes": timings, "text": text}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calliope.AI — TTS phoneme export (espeak-ng + timing JSON)"
    )
    parser.add_argument("text", help="Input text to synthesise")
    parser.add_argument(
        "--output-dir", default="/tmp", help="Directory for temp WAV (default: /tmp)"
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Omit wav_b64 from output (phoneme JSON only)",
    )
    args = parser.parse_args()

    result = export_phonemes(args.text, args.output_dir)
    if args.json_only:
        result["wav_b64"] = None

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
