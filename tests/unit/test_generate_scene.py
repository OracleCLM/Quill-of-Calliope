"""Unit test per scripts/generate_scene.py — _sanitize_user_prompt e _build_variant_prompt."""
from __future__ import annotations

from scripts.generate_scene import (
    _PROMPT_INJECTION_GUARD,
    _STYLE_DIRECTIVES,
    _build_variant_prompt,
    _sanitize_user_prompt,
)


def test_sanitize_empty():
    assert _sanitize_user_prompt("") == ""


def test_sanitize_truncation():
    long_text = "a" * 5000
    result = _sanitize_user_prompt(long_text)
    assert len(result) == 4000


def test_sanitize_injection_ignore_previous():
    assert _sanitize_user_prompt("IGNORE PREVIOUS") == "[IGNORE PREVIOUS]"


def test_sanitize_injection_system():
    assert _sanitize_user_prompt("SYSTEM:") == "[SYSTEM:]"


def test_sanitize_injection_assistant():
    assert _sanitize_user_prompt("ASSISTANT:") == "[ASSISTANT:]"


def test_sanitize_injection_user():
    assert _sanitize_user_prompt("USER:") == "[USER:]"


def test_sanitize_injection_instructions_word_boundary():
    # \b prima di ### richiede un word-char precedente (es. lettera)
    assert _sanitize_user_prompt("a### Instructions") == "a[### Instructions]"


def test_sanitize_control_chars():
    result = _sanitize_user_prompt("\x00a\nb\tc\x7f")
    assert result == " a\nb\tc "


def test_build_known_style():
    res = _build_variant_prompt("base", "combat", "descriptive")
    assert _STYLE_DIRECTIVES["descriptive"] in res


def test_build_unknown_style():
    res = _build_variant_prompt("base", "combat", "unknown_style")
    assert "Style directive: write in unknown_style style." in res


def test_build_contains_guard():
    res = _build_variant_prompt("base", "combat", "descriptive")
    assert _PROMPT_INJECTION_GUARD in res


def test_build_contains_prompt():
    res = _build_variant_prompt("my prompt", "combat", "descriptive")
    assert "my prompt" in res


def test_build_scene_type():
    res = _build_variant_prompt("base", "exploration", "descriptive")
    assert "exploration" in res


def test_build_injection_neutralized():
    res = _build_variant_prompt("IGNORE PREVIOUS", "combat", "descriptive")
    assert "[IGNORE PREVIOUS]" in res
    assert "IGNORE PREVIOUS" not in res.replace("[IGNORE PREVIOUS]", "")
