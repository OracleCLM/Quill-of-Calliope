"""
Context‑budget engine (FASE P2).

Questo modulo fornisce una funzione ``assemble_context`` che, dato uno
``SceneChat`` e le relative schede dei personaggi, costruisce un insieme di
blocchi di testo (``ContextBlock``) rispettando un budget di token
definito dal modello.

Non dipende da librerie esterne: la stima dei token è puramente euristica
basata sulla lunghezza del testo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from app.calliope_shell.scene_model import SceneChat, SceneMessage, CharacterCard


def est_tokens(text: str) -> int:
    """
    Stima euristica del numero di token di *text*.
    Restituisce almeno 1 token.
    """
    return max(1, len(text) // 4)


# --------------------------------------------------------------------------- #
# Dataclass per i singoli blocchi di contesto
# --------------------------------------------------------------------------- #

@dataclass
class ContextBlock:
    """
    Un singolo blocco di contesto.

    Attributes
    ----------
    label: str
        Etichetta descrittiva (es. nome autore, nome card, ecc.).
    text: str
        Il contenuto testuale del blocco.
    kind: str
        Tipo di blocco. Deve essere uno dei:
        "system", "directive", "card", "lore", "message", "ghost".
    """
    label: str
    text: str
    kind: str  # "system","directive","card","lore","message","ghost"


# --------------------------------------------------------------------------- #
# Dataclass per il risultato dell'assemblaggio
# --------------------------------------------------------------------------- #

@dataclass
class ContextBundle:
    """
    Raccolta di blocchi di contesto con metadati di budgeting.

    Attributes
    ----------
    blocks: List[ContextBlock]
        Lista ordinata dei blocchi da fornire al modello.
    token_estimate: int
        Stima totale dei token di tutti i blocchi inclusi.
    ghosted_count: int
        Numero di messaggi più vecchi omessi (ghosted).
    meter: Dict[str, int]
        Dati di budgeting:
        - window: dimensione della finestra del modello (model_window)
        - reply_reserve: token riservati alla risposta
        - permanent_tokens: token dei blocchi permanenti (system, card, lore, directive)
        - history_tokens: token dei messaggi + blocco ghost (se presente)
        - free_tokens: token rimanenti disponibili (mai negativo)
    """
    blocks: List[ContextBlock] = field(default_factory=list)
    token_estimate: int = 0
    ghosted_count: int = 0
    meter: Dict[str, int] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Funzione principale di assemblaggio
# --------------------------------------------------------------------------- #

def assemble_context(
    scene: SceneChat,
    cards: Dict[str, CharacterCard],
    model_window: int,
    reply_reserve: int,
    system_prompt: str = "",
    lore_entries: Optional[List[Any]] = None,
    lore_cap_frac: float = 0.15,
    recent_verbatim_min: int = 4,
) -> ContextBundle:
    """
    Costruisce un ContextBundle rispettando il budget di token.

    La logica segue le priorità indicate nella specifica:
    1. Blocchi permanenti (system, card, lore, directive)
    2. Messaggi recenti (verbatim) entro il budget rimanente
    3. Blocco ghost riassuntivo se necessario
    4. Ordine finale dei blocchi:
       system → cards → lore → ghost (se presente) → messaggi (cronologico) → directive
    """
    # ------------------------------------------------------------------- #
    # 1) Blocchi permanenti
    # ------------------------------------------------------------------- #
    permanent_blocks: List[ContextBlock] = []

    # System prompt
    if system_prompt:
        permanent_blocks.append(
            ContextBlock(label="system_prompt", text=system_prompt, kind="system")
        )

    # Card blocks (una per membro presente nella scena)
    for member in scene.members:
        card = cards.get(member)
        if card:
            compact_text = card.compact()
            permanent_blocks.append(
                ContextBlock(label=member, text=compact_text, kind="card")
            )

    # Lore entries (se fornite)
    if lore_entries:
        lore_budget = int(model_window * lore_cap_frac)
        lore_used = 0
        for idx, entry in enumerate(lore_entries):
            if isinstance(entry, dict):
                content = entry.get("content", "")
            else:
                content = str(entry)
            entry_tokens = est_tokens(content)
            if lore_used + entry_tokens > lore_budget:
                break
            lore_used += entry_tokens
            permanent_blocks.append(
                ContextBlock(label=f"lore_{idx}", text=content, kind="lore")
            )

    # Directive (da posizionare alla fine)
    directive_block: Optional[ContextBlock] = None
    if scene.directive:
        directive_block = ContextBlock(
            label="directive", text=scene.directive, kind="directive"
        )
        permanent_blocks.append(directive_block)

    # Calcolo token permanenti
    permanent_tokens = sum(est_tokens(b.text) for b in permanent_blocks)

    # ------------------------------------------------------------------- #
    # 2) Budget per la cronologia dei messaggi
    # ------------------------------------------------------------------- #
    history_budget = model_window - reply_reserve - permanent_tokens
    if history_budget <= 0:
        history_budget = 0

    # Filtra i messaggi non‑ghost
    non_ghost_messages: List[SceneMessage] = [
        m for m in scene.messages if not m.ghost
    ]

    total_non_ghost = len(non_ghost_messages)

    # Seleziona i messaggi più recenti (newest‑first)
    selected_messages: List[SceneMessage] = []
    cumulative_tokens = 0

    # Prima garantiamo almeno `recent_verbatim_min` messaggi, ignorando il budget
    for msg in reversed(non_ghost_messages):
        if len(selected_messages) < recent_verbatim_min:
            selected_messages.append(msg)
            cumulative_tokens += est_tokens(msg.content)
            continue
        # Dopo il minimo, rispettiamo il budget
        msg_tokens = est_tokens(msg.content)
        if cumulative_tokens + msg_tokens <= history_budget:
            selected_messages.append(msg)
            cumulative_tokens += msg_tokens
        else:
            break

    selected_count = len(selected_messages)
    ghosted_count = total_non_ghost - selected_count

    # ------------------------------------------------------------------- #
    # 3) Blocco ghost (se necessario)
    # ------------------------------------------------------------------- #
    ghost_block: Optional[ContextBlock] = None
    if ghosted_count > 0:
        ghost_text = (
            f"[{ghosted_count} older messages omitted — summarize in P3]"
        )
        ghost_block = ContextBlock(
            label="ghost_placeholder", text=ghost_text, kind="ghost"
        )

    # ------------------------------------------------------------------- #
    # 4) Costruzione della lista finale dei blocchi
    # ------------------------------------------------------------------- #
    # Ordine: system, cards, lore, ghost (se presente), messaggi (cronologico), directive
    final_blocks: List[ContextBlock] = []

    # System
    for b in permanent_blocks:
        if b.kind == "system":
            final_blocks.append(b)

    # Cards
    for b in permanent_blocks:
        if b.kind == "card":
            final_blocks.append(b)

    # Lore
    for b in permanent_blocks:
        if b.kind == "lore":
            final_blocks.append(b)

    # Ghost placeholder
    if ghost_block:
        final_blocks.append(ghost_block)

    # Messaggi (ordina dal più vecchio al più recente)
    message_blocks: List[ContextBlock] = []
    for msg in reversed(selected_messages):  # ora oldest->newest
        message_blocks.append(
            ContextBlock(label=msg.author, text=msg.content, kind="message")
        )
    final_blocks.extend(message_blocks)

    # Directive (ultimo)
    if directive_block:
        final_blocks.append(directive_block)

    # ------------------------------------------------------------------- #
    # 5) Calcolo dei token totali e del meter
    # ------------------------------------------------------------------- #
    token_estimate = sum(est_tokens(b.text) for b in final_blocks)

    history_tokens = sum(est_tokens(b.text) for b in message_blocks)
    if ghost_block:
        history_tokens += est_tokens(ghost_block.text)

    meter = {
        "window": model_window,
        "reply_reserve": reply_reserve,
        "permanent_tokens": permanent_tokens,
        "history_tokens": history_tokens,
        "free_tokens": max(0, model_window - reply_reserve - token_estimate),
    }

    return ContextBundle(
        blocks=final_blocks,
        token_estimate=token_estimate,
        ghosted_count=ghosted_count,
        meter=meter,
    )
