"""TTS text formatter — converte testo in TESTO-PER-LETTURA-VOCALE (cost-zero, deterministico).

Scope NM/Efesto: logica di formatting testuale (la voce/UI/GPU la fa SL con Piper).
Consolida la skill `efesto-tts-formatter` (prima solo prompt-based) in codice testato.

Pipeline prevista (WI atomici):
  strip_markdown → strip_code_fences → tables_to_prose → expand_symbols →
  lists_to_sentences → to_speakable (orchestratore).
"""
from __future__ import annotations


def strip_markdown(text: str) -> str:
    """
    Rimuove la formattazione markdown lasciando il testo leggibile ad alta voce (WI-TTS-1).

    Contratto (vedi tests/unit/test_tts_formatter.py):
      - **bold** / *italic* → testo nudo (ciao)
      - `inline code` → testo nudo (git status)
      - "# Header" → "Header" (rimuove i # iniziali + spazio)
      - "[testo](url)" → "testo" (tiene il testo del link, scarta l'URL)
      - marcatori di lista iniziali ("- ", "* ", "1. ") → rimossi (la lista→frasi è WI-TTS-5)
      - testo già piano → invariato
    """
    raise NotImplementedError("WI-TTS-1: implementazione aider")
