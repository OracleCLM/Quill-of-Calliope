"""
Retrieval helpers + refine-fn per context injection (E1/E2/E3).

- lore_retrieval_for_scene  → voci lore rilevanti (E1)
- sheet_retrieval_for_scene → schede personaggi attivi in scena (E2)
- build_refine_prompt       → prompt strutturato con lore+schede (C2-design)
- refine_message_via_gateway → chiama il gateway e ritorna content_enhanced (E3)
- apply_refine_to_message   → pipeline completa: recupera, raffina, scrive DB (E3)
"""
from __future__ import annotations

import os
import sqlite3
from typing import List, Optional

import requests

from app.calliope_shell.lore_kb import LoreEntry, LoreStore
from app.db.characters import list_characters_in_scene

_DEFAULT_GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8766")
_DEFAULT_REFINE_MODEL = "llama-3.3-70b-versatile"
_DEFAULT_REFINE_PROVIDER = "groq"


def lore_retrieval_for_scene(
    text: str,
    lore_store: LoreStore,
    max_entries: int = 20,
) -> List[LoreEntry]:
    """Ritorna le voci lore rilevanti per il testo della scena (E1).

    Delega a LoreStore.triggered_entries: constant entries + key-match.
    """
    return lore_store.triggered_entries(text, max_entries=max_entries)


def sheet_retrieval_for_scene(
    conn: sqlite3.Connection,
    scene_id: str,
) -> List[dict]:
    """Ritorna le schede dei personaggi attivi nella scena (E2).

    Per ogni personaggio nel roster (scene_characters), recupera i blocchi
    di testo in character_sheets associati tramite character_id.

    Returns list of {"name": str, "role": str, "sheets": [str, ...]}.
    """
    chars = list_characters_in_scene(conn, scene_id)
    results: List[dict] = []
    for char in chars:
        char_id = char.get("id")
        char_name = char.get("name", "")
        role = char.get("role", "")
        sheets: List[str] = []
        if char_id:
            cur = conn.execute(
                "SELECT content FROM character_sheets"
                " WHERE character_id = ? ORDER BY position_order",
                (char_id,),
            )
            sheets = [row[0] for row in cur.fetchall()]
        results.append({"name": char_name, "role": role, "sheets": sheets})
    return results


# ── C2-design: struttura del prompt ──────────────────────────────────────────

def build_refine_prompt(
    content_original: str,
    lore_entries: List[LoreEntry],
    char_sheets: List[dict],
) -> str:
    """Costruisce il prompt per il modello-forte (C2).

    Inietta schede personaggi attivi e voci lore come contesto.
    Il modello deve raffinare il testo grezzo mantenendo il registro letterario.
    """
    parts: List[str] = []

    if char_sheets:
        parts.append("=== SCHEDE PERSONAGGI ATTIVI ===")
        for c in char_sheets:
            if c["sheets"]:
                parts.append(f"[{c['name']} — {c['role']}]")
                parts.extend(c["sheets"])

    if lore_entries:
        parts.append("=== LORE RILEVANTE ===")
        for e in lore_entries:
            parts.append(f"[{e.title}] {e.content}")

    parts.append("=== TESTO DA RAFFINARE ===")
    parts.append(content_original)
    parts.append(
        "Raffina il testo sopra in prosa letteraria di alta qualità,"
        " coerente con le schede e il lore forniti."
        " Rispondi con il solo testo raffinato, senza commenti."
    )
    return "\n".join(parts)


# ── E3: refine-fn ─────────────────────────────────────────────────────────────

def refine_message_via_gateway(
    content_original: str,
    lore_entries: List[LoreEntry],
    char_sheets: List[dict],
    gateway_url: str = _DEFAULT_GATEWAY_URL,
    provider: str = _DEFAULT_REFINE_PROVIDER,
    model: str = _DEFAULT_REFINE_MODEL,
    timeout: int = 30,
) -> str:
    """Chiama il gateway LLM con il prompt arricchito e ritorna il testo raffinato (E3)."""
    prompt = build_refine_prompt(content_original, lore_entries, char_sheets)
    resp = requests.post(
        f"{gateway_url}/llm_ask",
        json={"provider": provider, "model": model, "prompt": prompt},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("result") or data.get("text") or content_original


def apply_refine_to_message(
    conn: sqlite3.Connection,
    message_id: str,
    lore_store: Optional[LoreStore] = None,
    gateway_url: str = _DEFAULT_GATEWAY_URL,
    provider: str = _DEFAULT_REFINE_PROVIDER,
    model: str = _DEFAULT_REFINE_MODEL,
) -> str:
    """Pipeline E3: recupera contesto, raffina via gateway, scrive content_enhanced nel DB.

    Returns il testo raffinato (content_enhanced).
    """
    row = conn.execute(
        "SELECT scene_id, content_original FROM messages WHERE id = ?",
        (message_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"message {message_id!r} non trovato")
    scene_id, content_original = row[0], row[1]

    lore_entries: List[LoreEntry] = []
    if lore_store is not None:
        lore_entries = lore_retrieval_for_scene(content_original or "", lore_store)
    char_sheets = sheet_retrieval_for_scene(conn, scene_id)

    refined = refine_message_via_gateway(
        content_original or "",
        lore_entries,
        char_sheets,
        gateway_url=gateway_url,
        provider=provider,
        model=model,
    )
    conn.execute(
        "UPDATE messages SET content_enhanced = ? WHERE id = ?",
        (refined, message_id),
    )
    conn.commit()
    return refined
