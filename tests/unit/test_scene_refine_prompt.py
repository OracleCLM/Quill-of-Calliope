"""Test per build_refine_prompt (C2 — contratto prompt-injection scene-chat)."""

from app.calliope_shell.lore_kb import LoreEntry
from app.calliope_shell.scene_refine import build_refine_prompt


def _sheet():
    return {
        "character_id": "c1",
        "name": "Aria",
        "role": "protagonist",
        "traits": ["brave", "wry"],
        "backstory": "Cresciuta tra i ghiacci del nord.",
        "speech_pattern": {"tone": "calm", "register": "formal"},
    }


def test_content_always_present():
    prompt = build_refine_prompt("Aria draws her blade.")
    assert "Aria draws her blade." in prompt
    assert "## Testo da raffinare" in prompt
    # Senza schede/lore i blocchi opzionali non compaiono.
    assert "## Personaggi attivi" not in prompt
    assert "## Lore rilevante" not in prompt


def test_sheets_injected():
    prompt = build_refine_prompt("testo", sheets=[_sheet()])
    assert "## Personaggi attivi in scena" in prompt
    assert "Aria" in prompt
    assert "protagonist" in prompt
    assert "brave" in prompt
    # speech_pattern serializzato.
    assert "tone: calm" in prompt
    assert "Cresciuta tra i ghiacci" in prompt


def test_lore_injected_loreentry_object():
    entry = LoreEntry(id="e-drago", title="Drago del Nord", content="Antico custode.")
    prompt = build_refine_prompt("testo", lore=[entry])
    assert "## Lore rilevante" in prompt
    assert "Drago del Nord" in prompt
    assert "Antico custode." in prompt


def test_lore_injected_mapping():
    prompt = build_refine_prompt(
        "testo", lore=[{"title": "Fazione X", "content": "Mercanti."}]
    )
    assert "Fazione X" in prompt
    assert "Mercanti." in prompt


def test_speaker_voice_block():
    prompt = build_refine_prompt("testo", speaker="Aria")
    assert "## Voce richiesta" in prompt
    assert "Aria" in prompt


def test_full_assembly_order():
    prompt = build_refine_prompt(
        "Aria parla.",
        sheets=[_sheet()],
        lore=[LoreEntry(id="e", title="L", content="c")],
        speaker="Aria",
    )
    # Ordine: sistema -> personaggi -> lore -> voce -> testo.
    i_sys = prompt.index("assistente di scrittura")
    i_chars = prompt.index("## Personaggi attivi")
    i_lore = prompt.index("## Lore rilevante")
    i_voice = prompt.index("## Voce richiesta")
    i_text = prompt.index("## Testo da raffinare")
    assert i_sys < i_chars < i_lore < i_voice < i_text
