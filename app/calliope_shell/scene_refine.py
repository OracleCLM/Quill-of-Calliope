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

import os
import random
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence

import requests


GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8766")

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


# Override runtime del profilo-scrittura (switch cloud/locale dalla UI, senza restart).
# "" = nessun override (usa il default = cloud da env). Valori: "cloud" | "local".
_write_profile_override: Dict[str, str] = {}


def write_profiles() -> Dict[str, tuple]:
    """I due profili-scrittura VISION (switch cloud/locale), configurabili via env.

    - CLOUD (default): gateway strong+uncensored. ``CALLIOPE_WRITE_PROVIDER`` /
      ``CALLIOPE_WRITE_MODEL`` (default ``cerebras`` / ``zai-glm-4.7``).
    - LOCAL (opzione-privacy, ceiling da testare): ``CALLIOPE_WRITE_LOCAL_PROVIDER`` /
      ``CALLIOPE_WRITE_LOCAL_MODEL`` (default ``ollama`` / ``dolphin-mistral:7b``).
    """
    return {
        "cloud": (
            os.getenv("CALLIOPE_WRITE_PROVIDER", "cerebras"),
            os.getenv("CALLIOPE_WRITE_MODEL", "zai-glm-4.7"),
        ),
        "local": (
            os.getenv("CALLIOPE_WRITE_LOCAL_PROVIDER", "ollama"),
            os.getenv("CALLIOPE_WRITE_LOCAL_MODEL", "dolphin-mistral:7b"),
        ),
    }


def active_write_profile() -> str:
    """Nome del profilo attivo: override runtime se presente, altrimenti ``cloud``."""
    return _write_profile_override.get("profile", "cloud")


def set_write_profile(profile: str) -> None:
    """Imposta il profilo-scrittura attivo a runtime (``cloud`` | ``local``)."""
    if profile not in ("cloud", "local"):
        raise ValueError("profile must be 'cloud' or 'local'")
    _write_profile_override["profile"] = profile


def resolve_write_model() -> tuple[str, str]:
    """Risolve (provider, model) del modello-scrittura attivo (profilo cloud/local).

    Default = profilo CLOUD (VISION decisione #4). Switch a runtime via
    ``set_write_profile`` (UI) o via env per i default di ciascun profilo.

    Returns:
        Tupla ``(provider, model)``.
    """
    return write_profiles()[active_write_profile()]


def _default_ask(prompt: str, provider: str, model: str, timeout: int = 60) -> str:
    resp = requests.post(
        f"{GATEWAY_URL}/llm_ask",
        json={"provider": provider, "model": model, "prompt": prompt},
        timeout=timeout,
    )
    if resp.ok:
        data = resp.json()
        return data.get("content") or data.get("result") or ""
    return ""


# --------------------------------------------------------------------------- #
# Resilienza-503 del gateway-scrittura (bug refine-503).
#
# Comportamento (equivalente Tenacity + PyBreaker, qui in stdlib per non aggiungere
# dipendenze non installate a un'app già in produzione — swap-in banale in futuro):
#   - RETRY con backoff esponenziale + jitter, onorando l'header Retry-After, SOLO su
#     errori di throughput/overload (429-throughput, 5xx, timeout/connessione).
#   - NESSUN retry su errori definitivi: 400 (bad request), 401 (auth), 429-quota.
#   - FAILOVER lungo la chain di provider (primary -> fallback configurabili).
#   - CIRCUIT-BREAKER per-provider: dopo N fallimenti il provider è "aperto" e saltato
#     per un cooldown (evita di martellare un provider morto).
#   - In caso di esaurimento totale: WriteModelError("overloaded") -> la route traduce
#     in messaggio-utente pulito (NON errore grezzo, NON DOM rotto).
# --------------------------------------------------------------------------- #

_RETRYABLE_HTTP = {429, 500, 502, 503, 504}
_BREAKER_THRESHOLD = 3
_BREAKER_COOLDOWN_S = 30.0
_circuit_breakers: Dict[str, Dict[str, float]] = {}


class WriteModelError(Exception):
    """Errore del modello-scrittura, con ``kind`` per il mapping a messaggio-utente.

    kind: ``overloaded`` (riprova dopo) | ``auth`` | ``bad_request`` | ``unavailable``.
    """

    def __init__(self, kind: str, message: str) -> None:
        self.kind = kind
        super().__init__(message)


def reset_circuit_breakers() -> None:
    """Azzera lo stato dei breaker (usato dai test)."""
    _circuit_breakers.clear()


def _breaker_open(provider: str) -> bool:
    st = _circuit_breakers.get(provider)
    return bool(st and st.get("open_until", 0.0) > time.time())


def _breaker_fail(provider: str) -> None:
    st = _circuit_breakers.setdefault(provider, {"failures": 0.0, "open_until": 0.0})
    st["failures"] += 1
    if st["failures"] >= _BREAKER_THRESHOLD:
        st["open_until"] = time.time() + _BREAKER_COOLDOWN_S


def _breaker_ok(provider: str) -> None:
    _circuit_breakers[provider] = {"failures": 0.0, "open_until": 0.0}


def _parse_retry_after(resp: "requests.Response") -> Optional[float]:
    val = resp.headers.get("Retry-After")
    if not val:
        return None
    try:
        return max(0.0, float(val))
    except (TypeError, ValueError):
        return None


def _is_quota_error(status: int, code: str) -> bool:
    """429 può essere throughput (retry) o quota giornaliera (NO-retry)."""
    code = (code or "").lower()
    return status == 429 and (
        "quota" in code or "daily" in code or "tokens_per_day" in code or "insufficient" in code
    )


def write_model_chain() -> List[tuple]:
    """Chain (provider, model): primary (resolve_write_model) + fallback da env.

    ``CALLIOPE_WRITE_FALLBACKS`` = CSV ``provider:model`` (default groq -> openrouter).
    """
    chain: List[tuple] = [resolve_write_model()]
    raw = os.getenv(
        "CALLIOPE_WRITE_FALLBACKS",
        "groq:llama-3.3-70b-versatile,openrouter:qwen/qwen3-coder:free",
    )
    for item in raw.split(","):
        item = item.strip()
        if not item or ":" not in item:
            continue
        prov, mod = item.split(":", 1)
        pair = (prov.strip(), mod.strip())
        if pair[0] and pair[1] and pair not in chain:
            chain.append(pair)
    return chain


def _post_once(provider: str, model: str, prompt: str, timeout: int,
               max_attempts: int = 3) -> str:
    """Una POST al gateway con retry-backoff+jitter su errori di throughput.

    Ritorna il contenuto (può essere stringa vuota se il gateway risponde ok-ma-vuoto).
    Solleva WriteModelError su esito definitivo (auth/bad_request) o esaurimento retry.
    """
    last_kind, last_msg = "unavailable", "nessuna risposta"
    for attempt in range(max_attempts):
        # Backoff di default (esponenziale + jitter); sovrascritto da Retry-After se presente.
        delay = min(0.5 * (2 ** attempt) + random.uniform(0.0, 0.3), 8.0)
        try:
            resp = requests.post(
                f"{GATEWAY_URL}/llm_ask",
                json={"provider": provider, "model": model, "prompt": prompt},
                timeout=timeout,
            )
        except requests.RequestException as exc:
            last_kind, last_msg = "unavailable", f"connessione: {exc}"
        else:
            if resp.ok:
                try:
                    data = resp.json()
                except ValueError:
                    data = {}
                return data.get("content") or data.get("result") or ""
            status = resp.status_code
            try:
                body = resp.json()
            except ValueError:
                body = {}
            code = str(body.get("code") or body.get("type") or "")
            # Errori definitivi: NO retry, NO senso-failover su input errato.
            if status == 400:
                raise WriteModelError("bad_request", f"{status} {code}")
            if status in (401, 403):
                raise WriteModelError("auth", f"{status} {code}")
            if _is_quota_error(status, code):
                # quota esaurita su QUESTO provider → fallisci subito (il failover proverà altri).
                raise WriteModelError("overloaded", f"quota {status} {code}")
            if status not in _RETRYABLE_HTTP:
                raise WriteModelError("unavailable", f"{status} {code}")
            last_kind, last_msg = "overloaded", f"{status} {code or 'throughput'}"
            ra = _parse_retry_after(resp)
            if ra is not None:
                delay = min(ra + random.uniform(0.0, 0.3), 8.0)
        if attempt < max_attempts - 1:
            time.sleep(delay)
    raise WriteModelError(last_kind, last_msg)


def ask_with_failover(prompt: str, timeout: int = 60) -> str:
    """Chiama il gateway lungo la chain con retry + circuit-breaker + failover.

    Solleva WriteModelError se nessun provider risponde (la route lo traduce in 503-pulito).
    """
    errors: List[str] = []
    for provider, model in write_model_chain():
        if _breaker_open(provider):
            errors.append(f"{provider}: breaker-aperto")
            continue
        try:
            content = _post_once(provider, model, prompt, timeout)
        except WriteModelError as exc:
            if exc.kind == "bad_request":
                raise  # input errato: il failover non aiuta
            _breaker_fail(provider)
            errors.append(f"{provider}: {exc.kind}")
            continue
        if content:
            _breaker_ok(provider)
            return content
        # ok-ma-vuoto: tratta come fallimento di questo provider, prova il prossimo.
        _breaker_fail(provider)
        errors.append(f"{provider}: vuoto")
    raise WriteModelError("overloaded", "tutti i provider non disponibili (" + "; ".join(errors) + ")")


def refine_message(
    message_id: str,
    scene_id: str,
    conn,
    store,
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    ask=None,
    max_lore: int = 20,
) -> str:
    from app.db.messages import get_message_by_id

    from app.calliope_shell.scene_retrieval import (
        retrieve_scene_lore,
        retrieve_scene_sheets,
    )

    msg = get_message_by_id(conn, message_id)
    if msg is None:
        return ""
    content = msg["content_original"] or ""
    speaker = msg["author_name"]
    sheets = retrieve_scene_sheets(scene_id, conn)
    lore = retrieve_scene_lore(content, store, max_entries=max_lore)
    prompt = build_refine_prompt(
        content, sheets=sheets, lore=lore, speaker=speaker
    )
    if ask is not None:
        enhanced = ask(prompt) or ""
    elif provider and model:
        # Override esplicito: singolo provider, niente chain.
        enhanced = _post_once(provider, model, prompt, 60) or ""
    else:
        # Default: chain resiliente (primary=resolve_write_model + fallback, retry+breaker).
        # Può sollevare WriteModelError -> la route la traduce in messaggio-utente pulito.
        enhanced = ask_with_failover(prompt) or ""
    conn.execute(
        "UPDATE messages SET content_enhanced = ? WHERE id = ?",
        (enhanced, message_id),
    )
    conn.commit()
    return enhanced
