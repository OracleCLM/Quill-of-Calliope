"""TTS text formatter — converte testo in TESTO-PER-LETTURA-VOCALE (cost-zero, deterministico).

Scope NM/Efesto: logica di formatting testuale (la voce/UI/GPU la fa SL con Piper).
Consolida la skill `efesto-tts-formatter` (prima solo prompt-based) in codice testato.

Pipeline prevista (WI atomici):
  strip_markdown → strip_code_fences → tables_to_prose → expand_symbols →
  lists_to_sentences → to_speakable (orchestratore).
"""
from __future__ import annotations

import re


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
    # Rimuove **bold**
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    # Rimuove *italic*
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    # Rimuove `inline code`
    text = re.sub(r"`(.*?)`", r"\1", text)
    # Rimuove [link](url)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Rimuove header (# ## ...) all'inizio della riga
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)
    # Rimuove marcatori di lista (- e *) all'inizio della riga
    text = re.sub(r"^[-*]\s+", "", text, flags=re.MULTILINE)
    # Rimuove marcatori di lista numerati (1. 2. ...) all'inizio della riga
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)

    return text


def strip_code_fences(text: str) -> str:
    """
    Rimuove i blocchi di codice ```...``` (non vanno letti ad alta voce) (WI-TTS-2).

    Contratto (tests/unit/test_tts_formatter.py):
      - blocco "```\\ncode\\n```" → rimosso (sostituito da stringa vuota)
      - blocco con linguaggio "```python\\n...\\n```" → rimosso
      - testo fuori dai fence → invariato
    """
    # ```[lang]\n ... ``` (non-greedy, multilinea): sostituisci l'intero blocco con "".
    return re.sub(r"```[^\n]*\n.*?```", "", text, flags=re.DOTALL)


def tables_to_prose(text: str) -> str:
    """
    Rimuove le righe di tabella markdown (non vanno lette ad alta voce) (WI-TTS-3).

    Contratto: le righe che iniziano (dopo eventuale spazio) con '|' vengono rimosse;
    il resto del testo resta invariato.
    """
    # Scarta le righe la cui prima colonna non-spazio è '|' (riga di tabella markdown).
    kept = [ln for ln in text.split("\n") if not ln.lstrip().startswith("|")]
    return "\n".join(kept)


def expand_symbols(text: str) -> str:
    """
    Espande i simboli in parole leggibili ad alta voce (WI-TTS-4).

    Contratto: '&'->'e', '%'->' percento', '@'->' chiocciola'. Testo senza simboli invariato.
    """
    return text.replace("&", "e").replace("%", " percento").replace("@", " chiocciola")


def lists_to_sentences(text: str) -> str:
    """
    Converte gli elenchi puntati in frasi separate da punto (WI-TTS-5).

    Contratto: righe che iniziano (dopo spazi) con '- ' diventano frasi: il marcatore
    viene tolto e ogni voce termina con '. '. Testo non-lista invariato.
    Esempio: "- mela\\n- pera" -> "mela. pera."
    """
    lines = text.split("\n")
    if not any(ln.lstrip().startswith("- ") for ln in lines):
        return text  # testo non-lista invariato
    parts = []
    for ln in lines:
        s = ln.lstrip()
        if s.startswith("- "):
            parts.append(s[2:].strip() + ".")
        elif ln.strip():
            parts.append(ln)
    return " ".join(parts)


def to_speakable(text: str) -> str:
    """
    Orchestratore: applica in pipeline tutte le trasformazioni TTS (WI-TTS-6).

    Pipeline: strip_code_fences -> tables_to_prose -> strip_markdown ->
    lists_to_sentences -> expand_symbols. Ritorna prosa pronta per la lettura vocale.
    """
    text = strip_code_fences(text)
    text = tables_to_prose(text)
    text = strip_markdown(text)
    text = lists_to_sentences(text)
    text = expand_symbols(text)
    return text
