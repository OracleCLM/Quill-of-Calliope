"""Assemblatore-prompt CONDIVISO per i tool-di-scrittura di Calliope (M-B).

Oggi ``/api/draft``, ``/api/scene/refine`` e ``/api/arc/<id>/continue`` costruiscono
il contesto di generazione in modo divergente. Questo modulo lo unifica in UN solo
posto, secondo lo schema della proposta-redesign §(a)+(c):

    [SYSTEM base + data.system_prompt dei char-attivi]
    [CONTEXT permanent: per ogni char ATTIVO in scena (da scene_characters)
        name + description + personality + scenario + mes_example
        + extensions.calliope.speech_pattern/backstory
     + lore triggered_entries (testo)
     + char_memory retrieve]
    [HISTORY]
    [POST-HISTORY: data.post_history_instructions]
    [USER intent/testo]

Si appoggia ai SSOT helper Card V2 di ``app.db.characters``
(``load_card_v2`` / ``card_get`` / ``card_ext``) introdotti in M-A.

Il budget ADATTIVO-PER-MODELLO (doc R-CAP) è applicato dal modulo
``budget_adaptive`` con troncamento PRIORITIZZATO (char-attivi > lore > memory).
La posizione dell'informazione-chiave rispetta lost-in-the-middle: system in
testa, post-history-instructions in coda, materiale-bulk nel mezzo.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

logger = logging.getLogger(__name__)

# System-prompt base condiviso (verbo-agnostico): i verbi specifici
# (genera/continua/...) aggiungono la propria istruzione finale.
DEFAULT_SYSTEM_BASE = (
    "You are a literary fantasy RP writer producing high-quality English prose. "
    "Preserve each character's distinct voice, use vivid sensory detail, and "
    "maintain narrative continuity with the scene so far."
)


@dataclass
class AssembledContext:
    """Risultato dell'assemblaggio condiviso.

    ``full_prompt`` è il prompt finale pronto per il gateway. Gli altri campi
    sono i blocchi grezzi (utili per i verbi degeneri translate/summarize che
    saltano il contesto) + telemetria del troncamento.
    """

    system: str = ""
    char_blocks: List[str] = field(default_factory=list)
    lore_blocks: List[str] = field(default_factory=list)
    memory_blocks: List[str] = field(default_factory=list)
    history: str = ""
    post_history: str = ""
    user: str = ""
    full_prompt: str = ""
    truncation: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Raccolta blocchi-char dalle schede Card V2 SSOT
# --------------------------------------------------------------------------- #

def _card_block(card: Mapping[str, Any]) -> str:
    """Costruisce il blocco-testo di UN personaggio dalla sua Card V2.

    Usa SOLO i SSOT helper ``card_get`` / ``card_ext`` (nessun campo inventato).
    """
    from app.db.characters import card_ext, card_get  # noqa: PLC0415

    name = card_get(card, "name", "") or ""
    description = card_get(card, "description", "") or ""
    personality = card_get(card, "personality", "") or ""
    scenario = card_get(card, "scenario", "") or ""
    mes_example = card_get(card, "mes_example", "") or ""
    ext = card_ext(card, "calliope")
    speech = ext.get("speech_pattern") or ""
    backstory = ext.get("backstory") or ""

    parts: List[str] = [f"[{name}]"]
    if description:
        parts.append(f"Description: {description}")
    if personality:
        parts.append(f"Personality: {personality}")
    if scenario:
        parts.append(f"Scenario: {scenario}")
    if backstory:
        parts.append(f"Backstory: {backstory}")
    if speech:
        if isinstance(speech, Mapping):
            sp = ", ".join(f"{k}={v}" for k, v in speech.items() if v)
            if sp:
                parts.append(f"Speech: {sp}")
        else:
            parts.append(f"Speech: {speech}")
    if mes_example:
        parts.append(f"Example dialogue:\n{mes_example}")
    return "\n".join(parts)


def collect_active_cards(conn, char_names: List[str]) -> List[Dict[str, Any]]:
    """Carica le Card V2 SSOT dei personaggi attivi (by name), in ordine.

    Salta i nomi non trovati / vuoti senza sollevare.
    """
    from app.db.characters import load_card_v2  # noqa: PLC0415

    out: List[Dict[str, Any]] = []
    for name in char_names:
        if not name:
            continue
        try:
            card = load_card_v2(conn, name)
        except Exception:  # pragma: no cover - difensivo
            card = None
        if card:
            out.append(card)
    return out


def system_from_cards(cards: List[Mapping[str, Any]], base: str = DEFAULT_SYSTEM_BASE) -> str:
    """SYSTEM = base + i ``data.system_prompt`` non-vuoti dei char-attivi."""
    from app.db.characters import card_get  # noqa: PLC0415

    chunks = [base] if base else []
    for c in cards:
        sp = card_get(c, "system_prompt", "") or ""
        if sp.strip():
            chunks.append(sp.strip())
    return "\n\n".join(chunks)


def post_history_from_cards(cards: List[Mapping[str, Any]]) -> str:
    """POST-HISTORY = concatenazione dei ``data.post_history_instructions``."""
    from app.db.characters import card_get  # noqa: PLC0415

    chunks: List[str] = []
    for c in cards:
        phi = card_get(c, "post_history_instructions", "") or ""
        if phi.strip():
            chunks.append(phi.strip())
    return "\n\n".join(chunks)


# --------------------------------------------------------------------------- #
# Assemblatore principale CONDIVISO
# --------------------------------------------------------------------------- #

def assemble(
    *,
    conn,
    active_char_names: Optional[List[str]] = None,
    cards: Optional[List[Mapping[str, Any]]] = None,
    history: str = "",
    user_text: str = "",
    lore_blocks: Optional[List[str]] = None,
    memory_blocks: Optional[List[str]] = None,
    verb_instruction: str = "",
    system_base: str = DEFAULT_SYSTEM_BASE,
    model: Optional[str] = None,
    apply_budget: bool = True,
) -> AssembledContext:
    """Costruisce il contesto di generazione UNICO condiviso da tutti i verbi.

    Parameters
    ----------
    conn:
        Connessione SQLite (per caricare le Card V2 SSOT se ``cards`` è None).
    active_char_names:
        Nomi dei char ATTIVI in scena (da ``scene_characters``). Usati solo se
        ``cards`` non è fornito direttamente.
    cards:
        Card V2 già caricate (override esplicito; utile per i test).
    history:
        Cronologia-scena già formattata (HISTORY block).
    user_text:
        Intent operatore o testo-target (USER block).
    lore_blocks / memory_blocks:
        Testi di lore key-match e char_memory già recuperati.
    verb_instruction:
        Istruzione finale specifica del verbo (es. "Write the draft...").
    model:
        Modello attivo del gateway → seleziona il cap adattivo. Se None, il
        budget usa il default conservativo.
    apply_budget:
        Se False, salta il troncamento (verbi degeneri translate/summarize).
    """
    if cards is None:
        cards = collect_active_cards(conn, active_char_names or [])

    system = system_from_cards(cards, base=system_base)
    char_blocks = [_card_block(c) for c in cards]
    lore_blocks = list(lore_blocks or [])
    memory_blocks = list(memory_blocks or [])
    post_history = post_history_from_cards(cards)

    truncation: Dict[str, Any] = {"applied": False}
    if apply_budget:
        from app.calliope_shell.budget_adaptive import truncate_permanent  # noqa: PLC0415

        char_blocks, lore_blocks, memory_blocks, truncation = truncate_permanent(
            char_blocks=char_blocks,
            lore_blocks=lore_blocks,
            memory_blocks=memory_blocks,
            model=model,
            fixed_overhead=system + post_history + history + user_text + verb_instruction,
        )

    full_prompt = _render_prompt(
        system=system,
        char_blocks=char_blocks,
        lore_blocks=lore_blocks,
        memory_blocks=memory_blocks,
        history=history,
        post_history=post_history,
        user_text=user_text,
        verb_instruction=verb_instruction,
    )

    return AssembledContext(
        system=system,
        char_blocks=char_blocks,
        lore_blocks=lore_blocks,
        memory_blocks=memory_blocks,
        history=history,
        post_history=post_history,
        user=user_text,
        full_prompt=full_prompt,
        truncation=truncation,
        meta={
            "active_chars": len(cards),
            "lore_blocks": len(lore_blocks),
            "memory_blocks": len(memory_blocks),
            "model": model,
        },
    )


def _render_prompt(
    *,
    system: str,
    char_blocks: List[str],
    lore_blocks: List[str],
    memory_blocks: List[str],
    history: str,
    post_history: str,
    user_text: str,
    verb_instruction: str,
) -> str:
    """Compone il prompt finale con ordine posizionale lost-in-the-middle.

    system (testa) → CHARACTERS → LORE → CHAR MEMORY (bulk, mezzo) →
    HISTORY → POST-HISTORY → USER → verb_instruction (coda).
    """
    parts: List[str] = []
    if system:
        parts.append(system)
    if char_blocks:
        parts.append("\n--- CHARACTERS ---\n" + "\n\n".join(char_blocks))
    if lore_blocks:
        parts.append("\n--- LORE ---\n" + "\n".join(lore_blocks))
    if memory_blocks:
        parts.append("\n--- CHARACTER MEMORY ---\n" + "\n".join(memory_blocks))
    if history:
        parts.append("\n--- HISTORY ---\n" + history)
    if post_history:
        parts.append("\n--- POST-HISTORY INSTRUCTIONS ---\n" + post_history)
    if user_text:
        parts.append("\n--- USER INTENT ---\n" + user_text)
    if verb_instruction:
        parts.append("\n" + verb_instruction)
    return "\n".join(parts)
