"""Unit test per scripts/merge_char_sources.py (base zai-glm, fix Claude)."""
from __future__ import annotations

from datetime import timezone

from scripts.merge_char_sources import _parse_dt, _prefix_word_match, slugify


# ── slugify ───────────────────────────────────────────────────────────────────

def test_slugify_basic():
    assert slugify("Hello World") == "hello-world"


def test_slugify_unicode_kept():
    # \w mantiene caratteri unicode (é non rimosso)
    assert slugify("Café au Lait") == "café-au-lait"


def test_slugify_special_chars_removed_no_separator():
    # !@# rimossi, ma nessuno spazio tra hello e world → helloworld
    assert slugify("Hello!@#World") == "helloworld"


def test_slugify_underscores_to_hyphen():
    assert slugify("hello_world") == "hello-world"


def test_slugify_strip_leading_trailing():
    assert slugify("  -test- ") == "test"


def test_slugify_multiple_spaces_collapsed():
    assert slugify("a   b") == "a-b"


def test_slugify_empty():
    assert slugify("") == ""


# ── _prefix_word_match ─────────────────────────────────────────────────────────

def test_prefix_match_exact():
    assert _prefix_word_match("Aurora", ["Aurora"]) == "Aurora"


def test_prefix_match_name_starts_with_candidate():
    assert _prefix_word_match("Aurora of Winter", ["Aurora"]) == "Aurora"


def test_prefix_match_hyphen_boundary():
    assert _prefix_word_match("Jean-Luc", ["Jean"]) == "Jean"


def test_prefix_match_quote_boundary():
    assert _prefix_word_match("Luke's Hand", ["Luke"]) == "Luke"


def test_prefix_match_candidate_starts_with_name():
    assert _prefix_word_match("Aurora", ["Aurora of Winter"]) == "Aurora of Winter"


def test_prefix_match_no_match():
    assert _prefix_word_match("Bob", ["Alice"]) is None


def test_prefix_match_no_word_boundary():
    # "Aurorax" starts with "Aurora" but next char is 'x', not boundary
    assert _prefix_word_match("Aurorax", ["Aurora"]) is None


def test_prefix_match_empty_candidate_skipped():
    assert _prefix_word_match("Test", ["", "Test"]) == "Test"


def test_prefix_match_case_insensitive():
    assert _prefix_word_match("aurora", ["AURORA"]) == "AURORA"


# ── _parse_dt ─────────────────────────────────────────────────────────────────

def test_parse_dt_none():
    assert _parse_dt(None) is None


def test_parse_dt_empty_string():
    assert _parse_dt("") is None


def test_parse_dt_z_suffix():
    dt = _parse_dt("2023-01-01T12:00:00Z")
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.year == 2023


def test_parse_dt_with_offset():
    dt = _parse_dt("2023-01-01T12:00:00+02:00")
    assert dt is not None
    assert dt.tzinfo is not None


def test_parse_dt_naive_gets_utc():
    dt = _parse_dt("2023-01-01T12:00:00")
    assert dt is not None
    assert dt.tzinfo == timezone.utc


def test_parse_dt_invalid_returns_none():
    assert _parse_dt("not-a-date") is None
