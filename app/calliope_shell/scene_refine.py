"""Raffinamento-scrittura scene-chat: costruzione del prompt-injection (C2).

Questo modulo definisce il *contratto* di prompt-injection per il modello-scrittura
forte (gateway cloud, configurabile). La funzione ``build_refine_prompt`` è PURA e
deterministica: assembla in un unico prompt il testo da raffinare insieme al
contesto recuperato — schede dei personaggi attivi in scena (vedi
``retrieve_scene_sheets``) e voci di lore pertinenti per key-match (vedi
``retrieve_scene_lore``).

La refine-fn vera e propria (E3) consumerà questo prompt, lo invierà al gateway e
popolerà ``messages.content_enhanced``; qui NON avviene alcuna chiamata LLM.
"""

from __future__ import annotations

from typing import Any, List, Mapping, Optional, Sequence

# Istruzione-sistema: postura editoriale del modello-scrittura. Allineata alla
# VISION scene-chat (qualità letteraria inglese, uncensored se giustificato,
# preservazione fedele di significato/azioni).
_SYSTEM_INSTRUCTION = (
    "Sei un assistente di scrittura narrativa per un gioco di ruolo testuale. "
    "Raffina il TESTO fornito elevandone la qualità letteraria in inglese, "
    "preservando ESATTAMENTE significato, intenzioni, azioni e ordine degli eventi. "
    "Mantieni la coerenza con le schede dei personaggi e con la lore fornite. "
    "Rispetta la voce e i pattern linguistici di chi parla. "
    "Non censurare temi maturi quando sono narrativamente giustificati. "
    "Rispondi SOLO con la prosa raffinata, senza preamboli né commenti."
)


def _format_sheet(sheet: Mapping[str, Any]) -> str:
    """Riga compatta per una scheda-personaggio (output di ``retrieve_scene_sheets``)."""
    name = sheet.get("name") or "?"
    head: List[str] = [f"- {name}"]

    role = sheet.get("role")
    if role:
        head.append(f"(ruolo: {role})")

    traits = sheet.get("traits") or []
    if traits:
        head.append("tratti: " + ", ".join(str(t) for t in traits))

    speech = sheet.get("speech_pattern") or {}
    if isinstance(speech, Mapping) and speech:
        sp = "; ".join(f"{k}: {v}" for k, v in speech.items())
        head.append(f"voce: {sp}")
    elif speech and not isinstance(speech, Mapping):
        head.append(f"voce: {speech}")

    line = " — ".join(head)

    backstory = (sheet.get("backstory") or "").strip()
    if backstory:
        line += f"\n  background: {backstory}"
    return line


def _format_lore(entry: Any) -> str:
    """Riga compatta per una voce di lore (``LoreEntry`` o mapping equivalente)."""
    if isinstance(entry, Mapping):
        title = entry.get("title") or entry.get("id") or "?"
        content = entry.get("content") or ""
    else:
        title = getattr(entry, "title", None) or getattr(entry, "id", "?")
        content = getattr(entry, "content", "") or ""
    content = str(content).strip()
    return f"- {title}: {content}" if content else f"- {title}"


def build_refine_prompt(
    content: str,
    sheets: Optional[Sequence[Mapping[str, Any]]] = None,
    lore: Optional[Sequence[Any]] = None,
    speaker: Optional[str] = None,
) -> str:
    """Costruisce il prompt-injection per il modello-scrittura forte (PURA, no LLM).

    Args:
        content: Il testo del messaggio da raffinare (narratore o personaggio).
        sheets: Schede dei personaggi attivi in scena (output di
            ``retrieve_scene_sheets``); ognuna è un mapping con name/role/traits/
            speech_pattern/backstory.
        lore: Voci di lore pertinenti (output di ``retrieve_scene_lore``);
            ``LoreEntry`` o mapping con title/content.
        speaker: Nome di chi parla, per ancorare la voce (opzionale).

    Returns:
        Un singolo prompt-stringa pronto per il gateway ``/llm_ask``.
    """
    sections: List[str] = [_SYSTEM_INSTRUCTION]

    if sheets:
        block = ["## Personaggi attivi in scena"]
        block.extend(_format_sheet(s) for s in sheets)
        sections.append("\n".join(block))

    if lore:
        block = ["## Lore rilevante"]
        block.extend(_format_lore(e) for e in lore)
        sections.append("\n".join(block))

    if speaker:
        sections.append(
            f"## Voce richiesta\nIl testo è pronunciato/narrato da: {speaker}. "
            "Mantieni coerente la sua voce e i suoi pattern linguistici."
        )

    sections.append(f"## Testo da raffinare\n{content}")

    return "\n\n".join(sections)
