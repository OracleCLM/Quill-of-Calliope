"""Unit test per scripts/blend_scene.py.

Copre le funzioni pure:
  - parse_variants_file(content) → {int: {style, text}}
  - parse_blend_spec(spec)       → List[int]

blend_variants() richiede HTTP al gateway → non unit-testato qui.
"""
from __future__ import annotations

from scripts.blend_scene import parse_blend_spec, parse_variants_file


# ── parse_variants_file ───────────────────────────────────────────────────────

_TWO_VARIANTS = """\
## [V1] style=literary-gothic
First variant text here.
Long enough.

## [V2] style=action-fast
Second variant text.
Also long.

---
"""

_THREE_VARIANTS = """\
## [V1] style=poetic | hint extra
Alpha variant content.

## [V2] style=dramatic
Beta variant content.

## [V3] style=minimalist
Gamma variant.

---
"""


def test_parse_two_variants():
    variants = parse_variants_file(_TWO_VARIANTS)
    assert set(variants.keys()) == {1, 2}


def test_parse_variant_style():
    variants = parse_variants_file(_TWO_VARIANTS)
    assert variants[1]["style"] == "literary-gothic"
    assert variants[2]["style"] == "action-fast"


def test_parse_variant_text_stripped():
    variants = parse_variants_file(_TWO_VARIANTS)
    assert variants[1]["text"].startswith("First variant")
    assert not variants[1]["text"].startswith("\n")


def test_parse_three_variants():
    variants = parse_variants_file(_THREE_VARIANTS)
    assert set(variants.keys()) == {1, 2, 3}
    assert variants[3]["style"] == "minimalist"


def test_parse_variants_empty_string():
    assert parse_variants_file("") == {}


def test_parse_variants_extra_pipe_hint_ignored():
    variants = parse_variants_file(_THREE_VARIANTS)
    assert variants[1]["style"] == "poetic"


# ── parse_blend_spec ──────────────────────────────────────────────────────────

def test_parse_blend_spec_plus():
    assert parse_blend_spec("1+2") == [1, 2]


def test_parse_blend_spec_three():
    assert parse_blend_spec("1+2+3") == [1, 2, 3]


def test_parse_blend_spec_comma():
    assert parse_blend_spec("1,3") == [1, 3]


def test_parse_blend_spec_spaces():
    assert parse_blend_spec("2 3") == [2, 3]


def test_parse_blend_spec_single():
    assert parse_blend_spec("1") == [1]


def test_parse_blend_spec_non_digit_ignored():
    assert parse_blend_spec("1+x+2") == [1, 2]
