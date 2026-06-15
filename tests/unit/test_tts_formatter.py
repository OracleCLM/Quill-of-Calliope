"""Contract tests — TTS text formatter (NM/Efesto scope, cost-zero, aider-impl).

Modulo che converte una risposta testuale in TESTO-PER-LETTURA-VOCALE: strip
markdown/code/tabelle → prosa, espandi simboli, frasi brevi, liste come frasi.
Consolida la skill `efesto-tts-formatter` (prima solo prompt-based) in codice testato.

WI-TTS-1: strip_markdown — rimuove la formattazione markdown lasciando il testo leggibile.
"""
from app.tts_formatter import strip_markdown


def test_strip_bold_and_italic():
    assert strip_markdown("**ciao** e *mondo*") == "ciao e mondo"


def test_strip_inline_code():
    assert strip_markdown("usa `git status` ora") == "usa git status ora"


def test_strip_headers():
    assert strip_markdown("# Titolo\ntesto") == "Titolo\ntesto"


def test_strip_link_keeps_text():
    assert strip_markdown("vedi [la guida](http://x.io/y)") == "vedi la guida"


def test_plain_text_unchanged():
    assert strip_markdown("nessuna formattazione qui") == "nessuna formattazione qui"


def test_strip_bullet_markers():
    # i marcatori di lista vengono tolti (la lista→frasi è WI-TTS-5; qui solo i marker)
    assert strip_markdown("- primo\n- secondo") == "primo\nsecondo"


from app.tts_formatter import strip_code_fences  # noqa: E402


def test_strip_simple_code_fence():
    assert strip_code_fences("prima\n```\nx=1\n```\ndopo").strip() == "prima\n\ndopo".strip()


def test_strip_lang_code_fence():
    assert "import" not in strip_code_fences("vedi:\n```python\nimport os\n```\nfine")


def test_no_fence_unchanged():
    assert strip_code_fences("nessun blocco qui") == "nessun blocco qui"


from app.tts_formatter import tables_to_prose, expand_symbols  # noqa: E402


def test_tables_removed():
    out = tables_to_prose("intro\n| a | b |\n|---|---|\n| 1 | 2 |\noutro")
    assert "|" not in out and "intro" in out and "outro" in out


def test_no_table_unchanged():
    assert tables_to_prose("riga normale") == "riga normale"


def test_expand_ampersand_percent():
    assert expand_symbols("A & B") == "A e B"
    assert expand_symbols("50%") == "50 percento"


def test_expand_no_symbols_unchanged():
    assert expand_symbols("testo pulito") == "testo pulito"


from app.tts_formatter import lists_to_sentences, to_speakable  # noqa: E402


def test_bullets_to_sentences():
    assert lists_to_sentences("- mela\n- pera") == "mela. pera."


def test_non_list_unchanged():
    assert lists_to_sentences("frase normale") == "frase normale"


def test_to_speakable_strips_all():
    out = to_speakable("# Titolo\n```\ncode\n```\n- **uno** & due")
    assert "```" not in out and "#" not in out and "**" not in out and "&" not in out
    assert "uno" in out and "due" in out
