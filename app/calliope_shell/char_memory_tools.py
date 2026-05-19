"""Letta-pattern self-editing tools for Calliope char memory.

Ported from Vesta Minerva/memory_tree/self_editing_tools.py — adapted for:
- Pure SQLite (no vault markdown files)
- Sync execution (Flask/CLI context, not async)
- char_name scoping (facts are per-character)
"""
from __future__ import annotations

import logging
from typing import Optional

from app.calliope_shell.char_memory import (
    append_fact,
    replace_fact,
    retrieve_multi_signal,
    get_facts,
)

logger = logging.getLogger(__name__)

_VALID_SCOPES = {"L1", "L2"}


def char_memory_append(
    char_name: str,
    fact: str,
    scope: str = "L1",
) -> dict:
    """Append a new fact to char memory — no approval required (L1/L2 only).

    L0 is protected (character canon) and cannot be written here.
    Ported from Vesta memory_append tool (sync version).
    """
    if not char_name or not fact:
        return {"success": False, "error": "char_name and fact are required"}
    if scope not in _VALID_SCOPES:
        return {"success": False, "error": f"scope must be L1 or L2, got {scope!r}"}

    fact_id = append_fact(char_name, fact, scope=scope)
    if fact_id is None:
        return {"success": False, "error": "append_fact failed (see logs)"}
    return {
        "success": True,
        "fact_id": fact_id,
        "char_name": char_name,
        "scope": scope,
        "fact_preview": fact[:100],
    }


def char_memory_replace(
    char_name: str,
    old_fact: str,
    new_fact: str,
    scope: str = "L1",
    approved: bool = False,
) -> dict:
    """Replace old_fact with new_fact in char memory.

    Requires approved=True (approval gate — Letta pattern).
    L0 is always blocked. L1/L2 require explicit confirmation.
    """
    if not char_name or not old_fact or not new_fact:
        return {"success": False, "error": "char_name, old_fact, new_fact are required"}
    if scope == "L0":
        return {"success": False, "error": "L0 (character canon) is protected from writes"}
    if scope not in _VALID_SCOPES:
        return {"success": False, "error": f"scope must be L1 or L2, got {scope!r}"}
    if not approved:
        return {
            "success": False,
            "requires_approval": True,
            "message": f"Replace '{old_fact[:50]}...' in {char_name} [{scope}]? Pass approved=True to confirm.",
        }

    result = replace_fact(char_name, old_fact, new_fact, scope=scope)
    if result.get("replaced", 0) == 0:
        logger.warning("char_memory_replace: old_fact not found in %s [%s]", char_name, scope)
    return result


def char_memory_recall(
    char_name: str,
    query: str,
    top_k: int = 5,
) -> dict:
    """Recall facts for char_name relevant to query via multi-signal retrieval."""
    if not char_name or not query:
        return {"success": False, "error": "char_name and query are required"}
    results = retrieve_multi_signal(char_name, query, top_k=top_k)
    return {
        "success": True,
        "char_name": char_name,
        "query": query,
        "results": results,
        "count": len(results),
    }


def char_memory_list_facts(
    char_name: str,
    scope: Optional[str] = None,
) -> dict:
    """List all facts for a character, optionally filtered by scope."""
    facts = get_facts(char_name, scope=scope)
    return {
        "success": True,
        "char_name": char_name,
        "scope": scope,
        "facts": facts,
        "count": len(facts),
    }
