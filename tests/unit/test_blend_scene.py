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


# ── blend_variants / write_blended_output / main() ───────────────────────────

from scripts.blend_scene import blend_variants, main, write_blended_output  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402
import pytest  # noqa: E402
import sys  # noqa: E402


def test_blend_variants_success() -> None:
    variants = {1: {"style": "style1", "text": "text1"}}
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"result": "blended text"}
    with patch("scripts.blend_scene.requests.post", return_value=mock_resp):
        result, latency = blend_variants(variants, [1])
    assert result == "blended text"
    assert latency >= 0


def test_blend_variants_text_field_fallback() -> None:
    variants = {1: {"style": "style1", "text": "text1"}}
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"text": "via text field"}
    with patch("scripts.blend_scene.requests.post", return_value=mock_resp):
        result, _ = blend_variants(variants, [1])
    assert result == "via text field"


def test_blend_variants_no_valid_indices() -> None:
    with pytest.raises(ValueError, match="No valid variants found"):
        blend_variants({}, [99])


def test_blend_variants_exception_returns_error_string() -> None:
    variants = {1: {"style": "style1", "text": "text1"}}
    with patch("scripts.blend_scene.requests.post", side_effect=Exception("Network error")):
        result, latency = blend_variants(variants, [1])
    assert result == "[blend failed — LLM call error]"
    assert latency >= 0


def test_write_blended_output(tmp_path) -> None:
    output_path = tmp_path / "output.md"
    source_path = tmp_path / "source.md"
    write_blended_output(output_path, "blended content", [1, 2], "Test hint", 123, source_path)
    content = output_path.read_text(encoding="utf-8")
    assert "Scene Blend:" in content
    assert "blended content" in content
    assert "123ms" in content
    assert "Test hint" in content


def test_write_blended_output_default_hint(tmp_path) -> None:
    output_path = tmp_path / "out.md"
    source_path = tmp_path / "src.md"
    write_blended_output(output_path, "text", [1], None, 0, source_path)
    assert "(default)" in output_path.read_text(encoding="utf-8")


def test_main_file_not_found(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["blend_scene", str(tmp_path / "missing.md"), "--blend", "1"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


def test_main_no_variants_found(tmp_path, monkeypatch) -> None:
    f = tmp_path / "variants.md"
    f.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["blend_scene", str(f), "--blend", "1"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


def test_main_invalid_blend_spec(tmp_path, monkeypatch) -> None:
    f = tmp_path / "variants.md"
    f.write_text(_TWO_VARIANTS, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["blend_scene", str(f), "--blend", "invalid_spec"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


def test_main_success(tmp_path, monkeypatch) -> None:
    f = tmp_path / "variants.md"
    f.write_text(_TWO_VARIANTS, encoding="utf-8")
    out = tmp_path / "output.md"
    monkeypatch.setattr(sys, "argv", [
        "blend_scene", str(f), "--blend", "1", "--output", str(out), "--hint", "merge them",
    ])
    with patch("scripts.blend_scene.blend_variants", return_value=("Final blended text", 42)):
        main()
    content = out.read_text(encoding="utf-8")
    assert "Final blended text" in content
    assert "42ms" in content
    assert "merge them" in content
