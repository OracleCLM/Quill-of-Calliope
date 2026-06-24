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
