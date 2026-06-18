"""Budget ADATTIVO-PER-MODELLO + troncamento prioritizzato (doc R-CAP).

Implementa la raccomandazione del documento
``2026-06-18_calliope_token_budget_research.md`` §4:

    budget_effettivo = context_window x effective_factor   (~0.5, prudente RULER/NoLiMa)
    permanent_cap    = budget_effettivo x permanent_share   (~0.38)
    floor permanent  = 2.5k token (sicurezza JanitorAI)

Il ``permanent_cap`` è il tetto del blocco-permanente (schede char-attivi +
lore key-match + char_memory). Quando si supera, il troncamento è
PRIORITIZZATO e GRADUALE (mai hard-cut a metà frase):

    1. SCHEDE CHAR-ATTIVI  -> priorità MAX (mai droppate per intero)
    2. LORE KEY-MATCH      -> droppa i match deboli (in coda) per primi
    3. CHAR_MEMORY         -> priorità MIN (droppa lo storico vecchio per primo)

La stima-token riusa l'euristica condivisa di ``context_budget.est_tokens``.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

from app.calliope_shell.context_budget import est_tokens

# Parametri di partenza prudenti (doc R-CAP §4.3 / §5).
EFFECTIVE_FACTOR = 0.5
PERMANENT_SHARE = 0.38
PERMANENT_FLOOR = 2500  # token — floor minimo di sicurezza (lezione JanitorAI)

# Tabella minima da mantenere: SOLO {modello -> context_window}.
# Tutto il resto è formula. Chiavi normalizzate lowercase senza provider-prefix.
MODEL_CONTEXT_WINDOW: Dict[str, int] = {
    "zai-glm-4.7": 200_000,
    "gpt-oss-120b": 128_000,
    "llama-3.3-70b-versatile": 128_000,
    "llama-3.3-70b": 128_000,
    "deepseek-r1": 128_000,
    "deepseek-r1-0528": 128_000,
    "deepseek/deepseek-r1-0528": 128_000,
    "qwen3-coder": 256_000,  # claim 1M cappato a un effective realistico (doc §4.3)
    "qwen/qwen3-coder": 256_000,
    "dolphin-mistral:7b": 32_000,
    "dolphin-mistral": 32_000,
}

# Override puntuali (doc §4.3 nota reasoning-model): per R1 il modello consuma
# context anche per i token di *thinking* -> share-permanente più prudente.
PERMANENT_SHARE_OVERRIDE: Dict[str, float] = {
    "deepseek-r1": 0.28,
    "deepseek-r1-0528": 0.28,
    "deepseek/deepseek-r1-0528": 0.28,
}

# Context-window di default quando il modello è ignoto (conservativo).
DEFAULT_CONTEXT_WINDOW = 32_000


def _normalize(model: Optional[str]) -> str:
    # Rimuove suffissi OpenRouter (:free, :nitro, :beta, etc.) per il lookup.
    s = (model or "").strip().lower()
    if ":" in s:
        s = s.rsplit(":", 1)[0]
    return s


def context_window_for(model: Optional[str]) -> int:
    """context_window del modello; default conservativo se ignoto."""
    return MODEL_CONTEXT_WINDOW.get(_normalize(model), DEFAULT_CONTEXT_WINDOW)


def permanent_cap_for(model: Optional[str]) -> int:
    """permanent_cap = ctx x effective_factor x permanent_share, floor 2.5k."""
    ctx = context_window_for(model)
    share = PERMANENT_SHARE_OVERRIDE.get(_normalize(model), PERMANENT_SHARE)
    cap = int(ctx * EFFECTIVE_FACTOR * share)
    return max(cap, PERMANENT_FLOOR)


def active_model() -> Optional[str]:
    """Modello attivo del gateway dallo stato d'ambiente.

    Legge ``CALLIOPE_LLM_MODEL`` (allineato a llm_routing_state in server.py).
    Il toggle uncensored sposta su dolphin-mistral, ma quello è uno stato di
    processo: il chiamante può passare ``model`` esplicito per coerenza.
    """
    return os.getenv("CALLIOPE_LLM_MODEL")


def _truncate_block_to_tokens(text: str, max_tokens: int) -> str:
    """Tronca *text* a ~max_tokens su confine-parola (non a metà-frase)."""
    if max_tokens <= 0:
        return ""
    if est_tokens(text) <= max_tokens:
        return text
    # est_tokens = len//4 -> char-budget approssimato; taglio su spazio.
    char_budget = max_tokens * 4
    if char_budget >= len(text):
        return text
    cut = text.rfind(" ", 0, char_budget)
    if cut <= 0:
        cut = char_budget
    return text[:cut].rstrip() + " […]"


def truncate_permanent(
    *,
    char_blocks: List[str],
    lore_blocks: List[str],
    memory_blocks: List[str],
    model: Optional[str] = None,
    fixed_overhead: str = "",
) -> Tuple[List[str], List[str], List[str], Dict]:
    """Applica il cap adattivo con troncamento PRIORITIZZATO al blocco-permanente.

    Il blocco-permanente = char_blocks + lore_blocks + memory_blocks. Se la sua
    stima-token supera ``permanent_cap_for(model)``, taglia GRADUALMENTE dal
    basso verso l'alto: prima char_memory (storico vecchio), poi lore (match
    deboli, assunti in coda della lista), infine — solo se necessario —
    comprime le schede char meno-recenti (mai droppate per intero, l'ultima
    scheda è preservata).

    ``fixed_overhead`` (system + history + user + post-history + verb) NON viene
    troncato qui (vive ai bordi, lost-in-the-middle), ma è ignorato dal cap-
    permanente: il cap riguarda solo il blocco-permanente come da doc R-CAP.

    Returns
    -------
    (char_blocks, lore_blocks, memory_blocks, telemetry)
    """
    cap = permanent_cap_for(model)

    def _perm_tokens(cb, lb, mb) -> int:
        return sum(est_tokens(t) for t in cb + lb + mb)

    before = _perm_tokens(char_blocks, lore_blocks, memory_blocks)
    telemetry: Dict = {
        "applied": False,
        "model": model,
        "permanent_cap": cap,
        "permanent_tokens_before": before,
        "dropped_memory": 0,
        "dropped_lore": 0,
        "compressed_chars": 0,
    }

    if before <= cap:
        telemetry["permanent_tokens_after"] = before
        return char_blocks, lore_blocks, memory_blocks, telemetry

    telemetry["applied"] = True
    cb = list(char_blocks)
    lb = list(lore_blocks)
    mb = list(memory_blocks)

    # 1) CHAR_MEMORY (priorità MIN): droppa lo storico vecchio per primo.
    #    Assunzione: memory_blocks ordinati recente→vecchio (drop dal fondo).
    while mb and _perm_tokens(cb, lb, mb) > cap:
        mb.pop()
        telemetry["dropped_memory"] += 1

    # 2) LORE KEY-MATCH: droppa i match deboli (in coda) per primi.
    while lb and _perm_tokens(cb, lb, mb) > cap:
        lb.pop()
        telemetry["dropped_lore"] += 1

    # 3) SCHEDE CHAR-ATTIVI (priorità MAX): mai droppate per intero.
    #    Se ancora oltre cap, comprimi le schede meno-recenti (dal fondo),
    #    preservando SEMPRE almeno l'ultima scheda intera.
    if cb and _perm_tokens(cb, lb, mb) > cap:
        # quota per le schede = cap meno lore+memory residui
        non_char = sum(est_tokens(t) for t in lb + mb)
        char_budget = max(cap - non_char, 0)
        if char_budget <= 0:
            # estremo: tieni solo l'ultima scheda compressa al floor
            keep = cb[-1]
            cb = [_truncate_block_to_tokens(keep, max(PERMANENT_FLOOR // 4, 1))]
            telemetry["compressed_chars"] = 1
        else:
            per = max(char_budget // len(cb), 1)
            new_cb: List[str] = []
            compressed = 0
            for blk in cb:
                if est_tokens(blk) > per:
                    new_cb.append(_truncate_block_to_tokens(blk, per))
                    compressed += 1
                else:
                    new_cb.append(blk)
            cb = new_cb
            telemetry["compressed_chars"] = compressed

    telemetry["permanent_tokens_after"] = _perm_tokens(cb, lb, mb)
    return cb, lb, mb, telemetry
