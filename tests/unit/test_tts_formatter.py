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
