"""
summarizer – modulo P3 per la compressione della cronologia delle scene.

Fornisce:
* un alias di tipo ``SummarizerFn``;
* una funzione di default deterministica ``default_summarizer``;
* ``summarize_range`` per riassumere un intervallo di messaggi;
* ``CompressionResult`` dataclass;
* ``compress_history`` per generare i riassunti automatici;
* ``apply_ghosting`` per marcare i messaggi più vecchi come ghost.

Tutto è basato solo sulla libreria standard e sui tipi di ``scene_model``.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from app.calliope_shell.scene_model import SceneChat, SceneMessage

# --------------------------------------------------------------------------- #
# Tipo alias per la funzione di riassunto
# --------------------------------------------------------------------------- #

SummarizerFn = Callable[[str], str]


# --------------------------------------------------------------------------- #
# Summarizer di default – euristico, deterministico e testabile offline
# --------------------------------------------------------------------------- #

def default_summarizer(text: str) -> str:
    """
    Riassume ``text`` in modo deterministico senza ricorrere a modelli esterni.

    - Divide il testo in frasi usando il separatore ``'. '`` (fallback su
      ``'.'`` se necessario).
    - Prende le prime due frasi (o meno se il testo è più corto).
    - Tronca il risultato a circa 200 caratteri.
    - Aggiunge il prefisso ``'Summary: '``.

    Il risultato è stabile: chiamate successive con lo stesso input
    restituiscono la stessa stringa.
    """
    # Normalizza gli spazi
    cleaned = " ".join(text.split())
    # Split su ". " ma gestisce anche casi senza spazio
    sentences = cleaned.split(". ")
    if len(sentences) == 1:
        # Prova a splittare su '.' semplice
        sentences = cleaned.split(".")
    # Prendi al massimo le prime due frasi
    selected = sentences[:2]
    summary = ". ".join(s.strip() for s in selected if s).strip()
    # Aggiungi il punto finale se manca
    if summary and not summary.endswith("."):
        summary += "."
    # Troncamento a 200 caratteri (incluso prefisso)
    max_len = 200 - len("Summary: ")
    if len(summary) > max_len:
        summary = summary[:max_len].rstrip()
        # Assicura che non termini a metà di una parola
        if " " in summary:
            summary = summary.rsplit(" ", 1)[0]
        summary += "..."
    return f"Summary: {summary}"


# --------------------------------------------------------------------------- #
# Riassunto di un intervallo di messaggi (modalità manuale)
# --------------------------------------------------------------------------- #

def summarize_range(
    messages: List[SceneMessage],
    summarizer_fn: Optional[SummarizerFn] = None,
) -> str:
    """
    Riassume un intervallo di messaggi.

    - Concatena ``author: content`` per ciascun messaggio, separati da newline.
    - Applica ``summarizer_fn`` (o ``default_summarizer``) al testo concatenato.
    - Restituisce la stringa di riassunto, pronta per essere editata.
    """
    if not messages:
        return ""

    if summarizer_fn is None:
        summarizer_fn = default_summarizer

    concatenated = "\n".join(f"{msg.author}: {msg.content}" for msg in messages)
    return summarizer_fn(concatenated)


# --------------------------------------------------------------------------- #
# Risultato della compressione della cronologia
# --------------------------------------------------------------------------- #

@dataclass
class CompressionResult:
    """
    Contenitore dei risultati della compressione della cronologia.

    Attributes
    ----------
    kept : List[SceneMessage]
        Messaggi recenti mantenuti verbatim.
    summaries : List[str]
        Riassunti per ciascun blocco di messaggi più vecchi.
    ghosted_count : int
        Numero totale di messaggi compressi (non più verbatim).
    """
    kept: List[SceneMessage] = field(default_factory=list)
    summaries: List[str] = field(default_factory=list)
    ghosted_count: int = 0


# --------------------------------------------------------------------------- #
# Compressione automatica della cronologia (modalità auto)
# --------------------------------------------------------------------------- #

def compress_history(
    scene: SceneChat,
    keep_recent_n: int = 6,
    range_size: int = 6,
    summarizer_fn: Optional[SummarizerFn] = None,
) -> CompressionResult:
    """
    Genera un ``CompressionResult`` per la cronologia di ``scene``.

    - Mantiene gli ultimi ``keep_recent_n`` messaggi non‑ghost verbatim.
    - I messaggi più vecchi vengono suddivisi in blocchi di ``range_size``
      (cronologicamente) e ciascun blocco viene riassunto tramite
      ``summarize_range``.
    - Il conteggio ``ghosted_count`` indica quanti messaggi sono stati
      compressi.
    - Non muta l'oggetto ``scene``.
    """
    # Filtra i messaggi non‑ghost (quelli da considerare per la compressione)
    non_ghost = [m for m in scene.messages if not m.ghost]

    # Se non ci sono messaggi, ritorna risultato vuoto
    if not non_ghost:
        return CompressionResult()

    # Messaggi da tenere verbatim (gli ultimi N)
    kept = non_ghost[-keep_recent_n:] if keep_recent_n > 0 else []
    # Messaggi più vecchi da comprimere
    older = non_ghost[:-keep_recent_n] if keep_recent_n > 0 else non_ghost

    ghosted_count = len(older)

    # Genera i riassunti per blocchi di ``range_size``
    summaries: List[str] = []
    for start in range(0, len(older), range_size):
        block = older[start:start + range_size]
        summary = summarize_range(block, summarizer_fn)
        if summary:
            summaries.append(summary)

    return CompressionResult(kept=kept, summaries=summaries, ghosted_count=ghosted_count)


# --------------------------------------------------------------------------- #
# Applicazione del ghosting (marcatura dei messaggi più vecchi)
# --------------------------------------------------------------------------- #

def apply_ghosting(
    scene: SceneChat,
    keep_recent_n: int = 6,
) -> SceneChat:
    """
    Restituisce una copia di ``scene`` in cui tutti i messaggi più vecchi
    dell'ultimo ``keep_recent_n`` sono marcati ``ghost=True``.

    La scena originale non viene modificata.
    """
    # Copia profonda della scena (incluse le liste interne)
    scene_copy: SceneChat = copy.deepcopy(scene)

    total = len(scene_copy.messages)
    # Indice a partire dal quale i messaggi sono considerati "recenti"
    cutoff = max(0, total - keep_recent_n)

    for idx, msg in enumerate(scene_copy.messages):
        if idx < cutoff:
            msg.ghost = True
        # I messaggi recenti mantengono il valore originale (potrebbero già
        # essere ghost, ma la logica di chiamata prevede che non lo siano).

    return scene_copy
