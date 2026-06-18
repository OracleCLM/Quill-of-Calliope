"""GAP-55: test per _format_sheet, _format_lore, build_refine_prompt — helper puri."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.scene_refine import (
    _format_lore,
    _format_sheet,
    build_refine_prompt,
)


# ── _format_sheet ─────────────────────────────────────────────────────────────


def test_format_sheet_name_present():
    line = _format_sheet({"name": "Aurora"})
    assert "Aurora" in line


def test_format_sheet_missing_name_placeholder():
    line = _format_sheet({})
    assert "?" in line


def test_format_sheet_role_included():
    line = _format_sheet({"name": "Mao", "role": "protagonist"})
    assert "protagonist" in line


def test_format_sheet_traits_joined():
    line = _format_sheet({"name": "X", "traits": ["coraggioso", "leale"]})
    assert "coraggioso" in line
    assert "leale" in line


def test_format_sheet_speech_pattern_dict():
    line = _format_sheet({"name": "Y", "speech_pattern": {"tono": "formale"}})
    assert "formale" in line


def test_format_sheet_speech_pattern_string():
    line = _format_sheet({"name": "Z", "speech_pattern": "lento e riflessivo"})
    assert "lento e riflessivo" in line


def test_format_sheet_backstory_on_new_line():
    line = _format_sheet({"name": "A", "backstory": "Guerriera del nord"})
    assert "\n" in line
    assert "Guerriera del nord" in line


def test_format_sheet_empty_traits_omitted():
    line = _format_sheet({"name": "B", "traits": []})
    assert "tratti" not in line


def test_format_sheet_empty_backstory_omitted():
    line = _format_sheet({"name": "C", "backstory": ""})
    assert "background" not in line


# ── _format_lore ──────────────────────────────────────────────────────────────


def test_format_lore_mapping_with_content():
    line = _format_lore({"title": "Midgard", "content": "Il mondo centrale"})
    assert "Midgard" in line
    assert "Il mondo centrale" in line


def test_format_lore_mapping_no_content():
    line = _format_lore({"title": "Misterioso"})
    assert "Misterioso" in line


def test_format_lore_starts_with_dash():
    line = _format_lore({"title": "X", "content": "Y"})
    assert line.startswith("- ")


def test_format_lore_object_with_attrs():
    class FakeLore:
        title = "Drago"
        content = "Essere leggendario"

    line = _format_lore(FakeLore())
    assert "Drago" in line
    assert "Essere leggendario" in line


def test_format_lore_fallback_id_if_no_title():
    line = _format_lore({"id": "entry-42", "content": "contenuto"})
    assert "entry-42" in line


# ── build_refine_prompt ───────────────────────────────────────────────────────


def test_build_refine_prompt_contains_content():
    prompt = build_refine_prompt("Un drago attacca il castello.")
    assert "Un drago attacca il castello." in prompt


def test_build_refine_prompt_is_string():
    assert isinstance(build_refine_prompt("testo"), str)


def test_build_refine_prompt_no_sheets_no_section():
    prompt = build_refine_prompt("testo", sheets=None)
    assert "Personaggi attivi" not in prompt


def test_build_refine_prompt_sheets_section_present():
    sheets = [{"name": "Aurora", "role": "eroe"}]
    prompt = build_refine_prompt("testo", sheets=sheets)
    assert "Personaggi attivi" in prompt
    assert "Aurora" in prompt


def test_build_refine_prompt_lore_section_present():
    lore = [{"title": "Midgard", "content": "Il mondo centrale"}]
    prompt = build_refine_prompt("testo", lore=lore)
    assert "Lore rilevante" in prompt
    assert "Midgard" in prompt


def test_build_refine_prompt_no_lore_no_section():
    prompt = build_refine_prompt("testo", lore=None)
    assert "Lore rilevante" not in prompt


def test_build_refine_prompt_speaker_present():
    prompt = build_refine_prompt("testo", speaker="Kira")
    assert "Kira" in prompt
    assert "Voce richiesta" in prompt


def test_build_refine_prompt_no_speaker_no_section():
    prompt = build_refine_prompt("testo", speaker=None)
    assert "Voce richiesta" not in prompt


def test_build_refine_prompt_sections_separated():
    sheets = [{"name": "X"}]
    prompt = build_refine_prompt("testo", sheets=sheets)
    assert "\n\n" in prompt
