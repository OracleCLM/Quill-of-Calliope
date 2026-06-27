"""Endpoint UNIFICATO dei tool-di-scrittura: ``POST /api/write`` (M-B §c).

Collassa le 6 route divergenti (draft/continue/refine/translate/summarize/
lore-check) in un solo dispatcher che usa l'ASSEMBLATORE-PROMPT condiviso
(``prompt_assembler``) + il budget ADATTIVO-PER-MODELLO (``budget_adaptive``).

Contratto::

    POST /api/write
    {
      "action": "genera|continua|rifinisci|traduci|riassumi|coerenza",
      "scene_id": "...",
      "text": "...",          # testo-target (rifinisci/traduci/riassumi/coerenza)
      "intent_it": "...",      # intent operatore (genera/continua)
      "char_focus": "...",     # personaggio in focus (opzionale)
      "style_hints": "...",
      "direction": "IT_to_EN"  # solo traduci
    }

I verbi *con contesto* (genera/continua/rifinisci/coerenza) passano per
l'assemblatore condiviso → STESSO contesto a parità d'input. I verbi *degeneri*
(traduci/riassumi) sono trasformazioni senza-contesto (apply_budget=False).

Registrato in ``server.py`` con UNA riga (``register_write_routes(app)``).
Le route legacy restano intatte (back-compat): questo blueprint le AFFIANCA.
"""

from __future__ import annotations

import logging
import os

import requests
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

write_bp = Blueprint("write", __name__)

_VALID_ACTIONS = {
    "genera",
    "continua",
    "rifinisci",
    "traduci",
    "riassumi",
    "coerenza",
}
_VALID_DIRECTIONS = {"IT_to_EN", "EN_to_IT"}


def _gateway_url() -> str:
    return os.getenv("GATEWAY_URL", "http://localhost:8766")


def _active_model() -> str:
    try:
        from app.calliope_shell.scene_refine import resolve_write_model  # noqa: PLC0415
        return resolve_write_model()[1]
    except Exception:
        return os.getenv("CALLIOPE_LLM_MODEL", "gpt-oss-120b")


def _active_provider() -> str:
    try:
        from app.calliope_shell.scene_refine import resolve_write_model  # noqa: PLC0415
        return resolve_write_model()[0]
    except Exception:
        return os.getenv("CALLIOPE_LLM_PROVIDER", "cerebras")


def _gateway_text(data: dict) -> str:
    return data.get("result") or data.get("text") or data.get("content", "") or ""


# --------------------------------------------------------------------------- #
# Raccolta contesto-scena per i verbi con-contesto (condivisa)
# --------------------------------------------------------------------------- #

def _active_char_names(scene_id: str, char_focus: str = "") -> list[str]:
    """Nomi dei char ATTIVI in scena (da scene_characters), o [char_focus]."""
    if char_focus:
        return [char_focus]
    if not scene_id:
        return []
    try:
        from app.db import get_db  # noqa: PLC0415
        from app.db.characters import list_characters_in_scene  # noqa: PLC0415

        conn = get_db()
        rows = list_characters_in_scene(conn, scene_id)
        conn.close()
        return [r["name"] for r in rows]
    except Exception:
        return []


def _scene_history(scene_id: str, max_msgs: int = 50) -> str:
    """HISTORY-block: ultimi max_msgs messaggi della scena, formattati author: content."""
    if not scene_id:
        return ""
    try:
        from app.db import get_db  # noqa: PLC0415

        conn = get_db()
        rows = conn.execute(
            "SELECT author_name, content_original, content_enhanced FROM messages "
            "WHERE scene_id = ? ORDER BY position_order DESC LIMIT ?",
            (scene_id, max_msgs),
        ).fetchall()
        conn.close()
        lines = []
        for author_name, content_original, content_enhanced in reversed(rows):
            author = author_name or "?"
            content = content_original or content_enhanced or ""
            if content:
                lines.append(f"{author}: {content}")
        return "\n".join(lines)
    except Exception:
        return ""


def _lore_blocks(query: str) -> list[str]:
    if not query:
        return []
    try:
        from app.calliope_shell.lore_kb import LoreStore  # noqa: PLC0415

        store = LoreStore()
        entries = store.triggered_entries(query, max_entries=5)
        return [
            (f"[{e.title}] {e.content}" if getattr(e, "title", None) else e.content)
            for e in entries if e.content
        ]
    except Exception:
        return []


def _memory_blocks(char_names: list[str], query: str) -> list[str]:
    out: list[str] = []
    for cn in char_names[:3]:
        if not cn:
            continue
        try:
            from app.calliope_shell.char_memory import retrieve_multi_signal  # noqa: PLC0415

            hits = retrieve_multi_signal(cn, query, top_k=3)
            out.extend(f"{cn}: {h['fact_text']}" for h in hits[:2])
        except Exception:
            pass
    return out


def _assemble_for_scene(scene_id, intent, char_focus, history, verb_instruction):
    """Costruisce il contesto condiviso per i verbi con-scena.

    Restituisce ``AssembledContext`` (o None se l'assembler non è disponibile).
    """
    from app.calliope_shell.prompt_assembler import assemble  # noqa: PLC0415

    names = _active_char_names(scene_id, char_focus)
    query = intent or ""
    lore = _lore_blocks(query)
    memory = _memory_blocks(names, query)

    conn = None
    try:
        from app.db import get_db  # noqa: PLC0415

        conn = get_db()
        ctx = assemble(
            conn=conn,
            active_char_names=names,
            history=history,
            user_text=intent,
            lore_blocks=lore,
            memory_blocks=memory,
            verb_instruction=verb_instruction,
            model=_active_model(),
        )
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    return ctx


def _call_gateway(endpoint, payload, timeout=90):
    """POST al gateway; ritorna (text, error_tuple). error_tuple=None se ok."""
    try:
        resp = requests.post(f"{_gateway_url()}/{endpoint}", json=payload, timeout=timeout)
        resp.raise_for_status()
        return _gateway_text(resp.json()), None
    except requests.exceptions.ConnectionError:
        return "", (jsonify({"error": "LLM gateway not available", "code": "gateway_down"}), 503)
    except Exception as exc:  # noqa: BLE001
        logger.warning("/api/write gateway call failed: %s", exc)
        return "", (jsonify({"error": str(exc)}), 503)


# --------------------------------------------------------------------------- #
# Verbi
# --------------------------------------------------------------------------- #

def _verb_genera(body):
    scene_id = (body.get("scene_id") or "").strip()
    intent = (body.get("intent_it") or "").strip()
    char_focus = (body.get("char_focus") or "").strip()
    if not intent:
        return jsonify({"error": "intent_it is required"}), 400
    ctx = _assemble_for_scene(
        scene_id, intent, char_focus, _scene_history(scene_id),
        "Write the scene draft in English. Be literary and evocative. 200-500 words.",
    )
    text, err = _call_gateway(
        "llm_code",
        {"provider": _active_provider(), "prompt": ctx.full_prompt,
         "temperature": 0.7, "max_tokens": 4096},
    )
    if err:
        return err
    return jsonify({
        "action": "genera", "draft_text": text, "model_used": _active_model(),
        "context_used": ctx.meta, "truncation": ctx.truncation,
    })


def _verb_continua(body):
    scene_id = (body.get("scene_id") or "").strip()
    intent = (body.get("intent_it") or body.get("direction") or "").strip()
    char_focus = (body.get("char_focus") or "").strip()
    history = _scene_history(scene_id)
    ctx = _assemble_for_scene(
        scene_id, intent, char_focus, history,
        "Continue the scene from where the history leaves off. "
        "Keep voice and continuity. 150-400 words.",
    )
    text, err = _call_gateway(
        "llm_code",
        {"provider": _active_provider(), "prompt": ctx.full_prompt,
         "temperature": 0.7, "max_tokens": 4096},
    )
    if err:
        return err
    return jsonify({
        "action": "continua", "draft_text": text, "model_used": _active_model(),
        "context_used": ctx.meta, "truncation": ctx.truncation,
    })


def _verb_rifinisci(body):
    scene_id = (body.get("scene_id") or "").strip()
    text_target = (body.get("text") or "").strip()
    feedback = (body.get("intent_it") or body.get("style_hints") or "").strip()
    char_focus = (body.get("char_focus") or "").strip()
    if not text_target:
        return jsonify({"error": "text is required"}), 400
    instruction = (
        f"Original scene:\n{text_target}\n\n"
        f"Operator feedback: {feedback or '(improve prose quality)'}\n\n"
        "Rewrite the scene applying the feedback. Preserve key narrative beats."
    )
    ctx = _assemble_for_scene(scene_id, feedback, char_focus, _scene_history(scene_id), instruction)
    text, err = _call_gateway(
        "llm_ask",
        {"provider": "groq", "model": "llama-3.3-70b-versatile", "prompt": ctx.full_prompt},
        timeout=45,
    )
    if err:
        return err
    return jsonify({
        "action": "rifinisci", "refined_text": text, "model_used": _active_model(),
        "context_used": ctx.meta, "truncation": ctx.truncation,
    })


def _verb_coerenza(body):
    scene_id = (body.get("scene_id") or "").strip()
    text_target = (body.get("text") or "").strip()
    char_focus = (body.get("char_focus") or "").strip()
    if not text_target:
        return jsonify({"error": "text is required"}), 400
    instruction = (
        "You are a lore consistency checker for a fantasy RP world.\n"
        "Compare the DRAFT TEXT below against the CHARACTERS and LORE context.\n"
        f"DRAFT TEXT:\n{text_target[:3000]}\n\n"
        "Output a JSON object: {\"coherent\": true|false, \"issues\": [...]}. "
        "Respond ONLY with valid JSON, no markdown fences."
    )
    ctx = _assemble_for_scene(scene_id, text_target[:500], char_focus, "", instruction)
    text, err = _call_gateway(
        "llm_review",
        {"provider": "openrouter", "prompt": ctx.full_prompt, "temperature": 0.1},
        timeout=45,
    )
    if err:
        return err
    import json as _json  # noqa: PLC0415

    coherent, issues = True, []
    try:
        clean = text.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = _json.loads(clean)
        coherent = parsed.get("coherent", True)
        issues = parsed.get("issues", [])
    except Exception:
        coherent, issues = False, [{"severity": "warning", "description": "parse failed"}]
    return jsonify({
        "action": "coerenza", "coherent": coherent, "issues": issues,
        "context_used": ctx.meta, "truncation": ctx.truncation,
    })


def _verb_traduci(body):
    """Caso degenere: trasformazione senza-contesto."""
    text = (body.get("text") or "").strip()
    direction = body.get("direction", "IT_to_EN")
    if not text:
        return jsonify({"error": "text is required"}), 400
    if direction not in _VALID_DIRECTIONS:
        return jsonify({"error": f"direction must be one of {sorted(_VALID_DIRECTIONS)}"}), 400
    if direction == "IT_to_EN":
        system = ("You are a literary translator specializing in fantasy roleplay. "
                  "Translate Italian to English preserving tone and fantasy vocabulary. "
                  "Output ONLY the translation.")
        prompt = f"Translate to English:\n\n{text}"
    else:
        system = ("You are a literary translator specializing in fantasy roleplay. "
                  "Translate English to Italian preserving tone and fantasy vocabulary. "
                  "Output ONLY the translation.")
        prompt = f"Translate to Italian:\n\n{text}"
    out, err = _call_gateway(
        "llm_ask",
        {"provider": "groq", "model": "llama-3.3-70b-versatile",
         "prompt": prompt, "system": system, "temperature": 0.3},
        timeout=30,
    )
    if err:
        return err
    return jsonify({"action": "traduci", "translation": out,
                    "model_used": "groq/llama-3.3-70b-versatile"})


def _verb_riassumi(body):
    """Caso degenere: trasformazione senza-contesto."""
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    try:
        max_length = min(int(body.get("max_length", 200)), 500)
    except (TypeError, ValueError):
        max_length = 200
    prompt = (
        "Summarize the following roleplay / Discord conversation text.\n"
        "Output a JSON object with fields:\n"
        f"- \"summary\": concise summary (max {max_length} words)\n"
        "- \"key_facts\": list of 3-7 key facts\n\n"
        f"Text:\n{text[:5000]}\n\n"
        "Respond ONLY with valid JSON, no markdown fences."
    )
    out, err = _call_gateway(
        "llm_ask",
        {"provider": "groq", "model": "llama-3.3-70b-versatile",
         "prompt": prompt, "temperature": 0.2},
        timeout=30,
    )
    if err:
        return err
    import json as _json  # noqa: PLC0415

    summary, key_facts = out, []
    try:
        clean = out.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = _json.loads(clean)
        summary = parsed.get("summary", out)
        key_facts = parsed.get("key_facts", [])
    except Exception:
        pass
    return jsonify({"action": "riassumi", "summary": summary, "key_facts": key_facts,
                    "model_used": "groq/llama-3.3-70b-versatile"})


_DISPATCH = {
    "genera": _verb_genera,
    "continua": _verb_continua,
    "rifinisci": _verb_rifinisci,
    "coerenza": _verb_coerenza,
    "traduci": _verb_traduci,
    "riassumi": _verb_riassumi,
}


@write_bp.route("/api/write", methods=["POST"])
def write_dispatch():
    body = request.get_json(silent=True) or {}
    action = (body.get("action") or "").strip().lower()
    if action not in _VALID_ACTIONS:
        return jsonify({
            "error": f"action must be one of {sorted(_VALID_ACTIONS)}",
        }), 400
    handler = _DISPATCH[action]
    result = handler(body)
    # Audit hook (best-effort).
    try:
        from app.calliope_shell import audit_trail as _audit  # noqa: PLC0415

        _audit.log_event(
            "write.dispatch", subject=action,
            detail=(body.get("intent_it") or body.get("text") or "")[:120],
            metadata={"scene_id": body.get("scene_id", ""), "char_focus": body.get("char_focus", "")},
        )
    except Exception:
        pass
    return result


def register_write_routes(app) -> None:
    """Registra il blueprint /api/write (UNA riga in server.py)."""
    app.register_blueprint(write_bp)
