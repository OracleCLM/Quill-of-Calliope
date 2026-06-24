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
