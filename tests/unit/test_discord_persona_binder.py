"""Unit test per scripts/discord_persona_binder.py — parse_persona_trigger (pura)."""
from __future__ import annotations

from scripts.discord_persona_binder import parse_persona_trigger


def test_valid_simple():
    assert parse_persona_trigger("Alice: Hello world") == ("Alice", "Hello world")


def test_valid_with_spaces_in_name():
    assert parse_persona_trigger("John Doe: Hello world") == ("John Doe", "Hello world")


def test_valid_strip_outer_whitespace():
    assert parse_persona_trigger("  John Doe : Hello world  ") == ("John Doe", "Hello world")


def test_valid_unicode_name():
    assert parse_persona_trigger("Élise: Bonjour!") == ("Élise", "Bonjour!")


def test_valid_min_text_length():
    assert parse_persona_trigger("A: Hey") == ("A", "Hey")


def test_valid_dotall_newlines():
    result = parse_persona_trigger("Alice: text with\nnewlines")
    assert result == ("Alice", "text with\nnewlines")


def test_no_match_missing_space_after_colon():
    assert parse_persona_trigger("Alice:Hello world") == (None, None)


def test_no_match_text_too_short():
    assert parse_persona_trigger("A: Hi") == (None, None)


def test_no_match_digit_start():
    assert parse_persona_trigger("123: hello world") == (None, None)


def test_no_match_name_too_long():
    long_name = "A" * 42
    assert parse_persona_trigger(f"{long_name}: test") == (None, None)


def test_no_match_empty_string():
    assert parse_persona_trigger("") == (None, None)


def test_no_match_whitespace_only():
    assert parse_persona_trigger("  \t  ") == (None, None)
