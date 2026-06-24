"""
Unit test per _fts_escape in char_memory.py (FTS5 query builder).

Contratto:
  - token vuoti / solo whitespace → '""'
  - token brevi (<2 char) ignorati
  - token normali → "token"
  - token lunghi (≥8 char) → "token" OR "PREF"*
  - quote singole/doppie rimosse
  - multi-token → OR-joined
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.char_memory import _fts_escape


def test_empty_query():
    assert _fts_escape("") == '""'


def test_whitespace_only():
    assert _fts_escape("   ") == '""'


def test_single_char_ignored():
    assert _fts_escape("a") == '""'


def test_short_token():
    result = _fts_escape("ciao")
    assert '"ciao"' in result


def test_long_token_adds_prefix():
    # "addestrare" = 10 chars ≥ 8 → prefix "addes" (FTS_PREFIX_LEN=5)
    result = _fts_escape("addestrare")
    assert '"addestrare"' in result
    assert '"addes"*' in result


def test_multi_token_joined_with_or():
    result = _fts_escape("ciao bella")
    assert "OR" in result
    assert '"ciao"' in result
    assert '"bella"' in result


def test_removes_single_quotes():
    result = _fts_escape("Aurora's power")
    assert "'" not in result


def test_removes_double_quotes():
    result = _fts_escape('"quoted"')
    # Il token viene strip-pato delle doppie quote prima del wrapping
    assert '"quoted"' in result


def test_token_exactly_8_chars_gets_prefix():
    # "combatte" = 8 chars → prefix "comba" (length 5)
    result = _fts_escape("combatte")
    assert '"combatte"' in result
    assert '"comba"*' in result


def test_token_7_chars_no_prefix():
    # "strega_" = 7 chars → solo "strega" senza prefix
    result = _fts_escape("streghe")
    assert '"streghe"' in result
    assert "*" not in result
