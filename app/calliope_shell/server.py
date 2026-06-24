import logging
import os
from functools import lru_cache
from pathlib import Path

import chromadb
import requests
import yaml
from flask import Flask, jsonify, request, render_template

from app.calliope_shell.char_memory import get_char, list_chars, upsert_char
from app.calliope_shell.char_memory_tools import (
    char_memory_append,
    char_memory_replace,
    char_memory_recall,
    char_memory_list_facts,
)
from app.calliope_shell.characters_routes import register_character_routes
from app.calliope_shell.lore_routes import register_lore_routes
from app.calliope_shell.scenes_db_routes import register_scenes_db_routes
from app.calliope_shell.arcs_db_routes import register_arcs_db_routes
from app.scene_context import resolve_scene_context

logger = logging.getLogger(__name__)

_mascot_state: dict = {"emotion": "neutral", "intensity": 1.0, "scene_id": None}

_CHROMA_PATH = str(Path(__file__).parents[2] / ".chroma_calliope")
_SCENES_DIR = Path(__file__).parents[2] / "scenes"
_CHARS_DIR = Path(__file__).parents[2] / "characters"
_VALID_DIRECTIONS = {"IT_to_EN", "EN_to_IT"}


def _load_char_sheets(names: list[str]) -> list[dict]:
    import json as _json  # noqa: PLC0415
    sheets = []
    for name in names:
        found = False
        try:
            from app.db import get_db as _get_db  # noqa: PLC0415
            _conn = _get_db()
            cur = _conn.execute(
                "SELECT name, card_json FROM characters WHERE name = ? LIMIT 1",
                (name,),
            )
            row = cur.fetchone()
            _conn.close()
            if row:
                card: dict = {}
                try:
                    card = _json.loads(row["card_json"] or "{}") or {}
                except Exception:
                    pass
                sheets.append({
                    "name": row["name"],
                    "traits": card.get("traits", []),
                    "backstory": (card.get("backstory") or "")[:300],
                    "speech_pattern": card.get("speech_pattern", {}),
                    "race": card.get("race", ""),
                    "class": card.get("class", ""),
                })
                found = True
        except Exception:
            pass
        if found:
            continue
        # fallback YAML
        for p in _CHARS_DIR.glob("*.yaml"):
            if name.lower() in p.stem.lower():
                try:
                    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                    if isinstance(raw, dict):
                        sheets.append({
                            "name": raw.get("name", p.stem),
                            "traits": raw.get("traits", []),
                            "backstory": (raw.get("backstory") or "")[:300],
                            "speech_pattern": raw.get("speech_pattern", {}),
                            "race": raw.get("race", ""),
                            "class": raw.get("class", ""),
                        })
                except Exception:
                    pass
                break
    return sheets


def _search_lore(query: str, n: int = 3) -> list[str]:
    try:
        client = _chroma_client()
        col = client.get_collection("calliope_lore")
        results = col.query(query_texts=[query], n_results=n)
        return [doc[:300] for doc in (results.get("documents", [[]])[0])]
    except Exception:
        return []


@lru_cache(maxsize=1)
def _chroma_client():
    return chromadb.PersistentClient(path=_CHROMA_PATH)


def _detect_discord_bot() -> dict:
    """Detect Discord bot state — graceful-degradation pattern (Q6 code-prepared).

    Returns {up, reason, channels, last_msg_ts} so the UI widget can render
    both 'active' state (when bot eventually runs) and 'configure first' CTA
    without waiting on a code change.
    """
    import subprocess  # noqa: PLC0415
    token_configured = bool(os.environ.get("CALLIOPE_DISCORD_BOT_TOKEN", "").strip())
    try:
        out = subprocess.run(
            ["pgrep", "-fa", "scripts/discord_bot.py"],
            capture_output=True, text=True, timeout=2,
        )
        process_running = bool(out.stdout.strip())
    except Exception:
        process_running = False

    if process_running:
        return {
            "up": True, "code": 200, "latency_ms": None,
            "reason": "active",
            "token_configured": True,
            "channels": [], "last_msg_ts": None,
        }
    if not token_configured:
        return {
            "up": False, "code": None, "latency_ms": None,
            "reason": "token_not_configured",
            "token_configured": False,
            "channels": [], "last_msg_ts": None,
        }
    return {
        "up": False, "code": None, "latency_ms": None,
        "reason": "token_configured_but_bot_not_running",
        "token_configured": True,
        "channels": [], "last_msg_ts": None,
    }


def _safe_variants_path(user_path: str) -> Path:
    """Validate a variants file path supplied to /api/scene/blend.

    Why: /api/scene/variants writes to tempfile.mktemp() (system tmp dir,
    files named 'calliope_*.variants.md'). /api/scene/blend then reads via
    user-supplied path → path-traversal if unchecked (audit P1 #4, same
    vector as P0 #1 on /api/scene/refine).

    Allowed roots: tmp dir prefix + repo scenes/ dir. Filename must match
    the calliope_*.variants.md pattern produced by the variants route.
    """
    import tempfile as _tempfile  # noqa: PLC0415
    if not user_path:
        raise ValueError("empty path")
    candidate = Path(user_path).resolve()
    tmp_root = Path(_tempfile.gettempdir()).resolve()
    scenes_root = (Path(__file__).parents[2] / "scenes").resolve()
    name = candidate.name
    is_in_tmp = candidate.is_relative_to(tmp_root) if hasattr(candidate, "is_relative_to") else str(candidate).startswith(str(tmp_root) + "/")
    is_in_scenes = candidate.is_relative_to(scenes_root) if hasattr(candidate, "is_relative_to") else str(candidate).startswith(str(scenes_root) + "/")
    if not (is_in_tmp or is_in_scenes):
        raise ValueError(f"path outside allowed roots (tmp / scenes): {user_path}")
    if not (name.startswith("calliope_") and name.endswith(".variants.md")):
        raise ValueError(f"filename pattern mismatch (expected calliope_*.variants.md): {name}")
    return candidate


def _safe_read_scene_file(user_path: str) -> str:
    """Read a scene file, restricted to _SCENES_DIR.

    Why: prevents path-traversal (e.g. '../../.env') on /api/scene/* endpoints
    that accept a file path from the request body.
    """
    if not user_path:
        raise ValueError("empty path")
    candidate = Path(user_path)
    if not candidate.is_absolute():
        candidate = _SCENES_DIR / user_path
    resolved = candidate.resolve()
    scenes_root = _SCENES_DIR.resolve()
    try:
        resolved.relative_to(scenes_root)
    except ValueError as exc:
        raise ValueError(f"path outside scenes directory: {user_path}") from exc
    return resolved.read_text(encoding="utf-8")


def _load_emotion_map() -> dict:
    map_path = Path(__file__).parents[2] / "data" / "calliope_emotion_map.yaml"
    try:
        return yaml.safe_load(map_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        logger.warning("calliope_emotion_map.yaml load failed: %s", exc)
        return {}


def create_app():
    app = Flask(__name__)
    register_character_routes(app)
    register_lore_routes(app)
    register_scenes_db_routes(app)
    register_arcs_db_routes(app)

    FLASK_PORT = os.getenv("FLASK_PORT", "5000")
    ST_URL = os.getenv("ST_URL", "http://localhost:8001")
    MASCOT_WS_URL = os.getenv("MASCOT_WS_URL", "ws://localhost:9876")
    MASCOT_REST_URL = os.getenv("MASCOT_REST_URL", "http://localhost:9876")
    GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8766")

    # ── Core routes ──────────────────────────────────────────────────────────

    @app.route("/")
    def index():
        # Gap D: detect ST liveness for empty-state fallback
        st_alive = False
        try:
            r = requests.head(ST_URL, timeout=1)
            st_alive = r.status_code < 500
        except Exception:
            st_alive = False
        return render_template("shell.html", ST_URL=ST_URL, MASCOT_WS_URL=MASCOT_WS_URL, st_alive=st_alive)

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    _llm_routing_state: dict = {
        "provider": os.getenv("CALLIOPE_LLM_PROVIDER", "cerebras"),
        "model": os.getenv("CALLIOPE_LLM_MODEL", "gpt-oss-120b"),
        "uncensored": False,
    }
    _UNCENSORED_PROFILE = {
        "provider": "ollama",
        "model": os.getenv("CALLIOPE_OLLAMA_UNCENSORED_MODEL", "dolphin-mistral:7b"),
    }
    _DEFAULT_PROFILE = {
        "provider": os.getenv("CALLIOPE_LLM_PROVIDER", "cerebras"),
        "model": os.getenv("CALLIOPE_LLM_MODEL", "gpt-oss-120b"),
    }

    @app.route("/api/dashboard/llm_routing", methods=["GET"])
    def dashboard_llm_routing_get():
        return jsonify({
            "active_provider": _llm_routing_state["provider"],
            "active_model": _llm_routing_state["model"],
            "uncensored_active": _llm_routing_state["uncensored"],
            "uncensored_provider": _UNCENSORED_PROFILE["provider"],
            "uncensored_model": _UNCENSORED_PROFILE["model"],
            "default_provider": _DEFAULT_PROFILE["provider"],
            "default_model": _DEFAULT_PROFILE["model"],
        })

    @app.route("/api/dashboard/llm_routing", methods=["POST"])
    def dashboard_llm_routing_post():
        """Toggle between default tier and uncensored Ollama profile (Q3).

        Body: {"uncensored": true|false}. Persists in process memory; on
        Flask restart reverts to env defaults. Cross-request consistency is
        intentional — operator toggle is a session-scoped decision.
        """
        body = request.get_json(silent=True) or {}
        if "uncensored" not in body:
            return jsonify({"error": "missing 'uncensored' (bool) in body"}), 400
        target = bool(body["uncensored"])
        if target:
            _llm_routing_state["provider"] = _UNCENSORED_PROFILE["provider"]
            _llm_routing_state["model"] = _UNCENSORED_PROFILE["model"]
            _llm_routing_state["uncensored"] = True
        else:
            _llm_routing_state["provider"] = _DEFAULT_PROFILE["provider"]
            _llm_routing_state["model"] = _DEFAULT_PROFILE["model"]
            _llm_routing_state["uncensored"] = False
        # Audit hook (Sprint C2).
        try:
            from app.calliope_shell import audit_trail as _audit  # noqa: PLC0415
            _audit.log_event(
                "llm_routing.switch",
                subject=_llm_routing_state["provider"],
                detail=f"uncensored={'on' if _llm_routing_state['uncensored'] else 'off'}",
                metadata={"model": _llm_routing_state["model"]},
            )
        except Exception:
            pass
        return jsonify({
            "active_provider": _llm_routing_state["provider"],
            "active_model": _llm_routing_state["model"],
            "uncensored_active": _llm_routing_state["uncensored"],
        })

    @app.route("/api/dashboard/activity", methods=["GET"])
    def dashboard_activity():
        """Read audit_trail for the activity-feed panel (Sprint C3).

        Query params:
          mode: 'highlight' (default, operator-perceived events) |
                'verbose' (all 13 write kinds)
          limit: 1..100 (default 20)
        """
        from app.calliope_shell import audit_trail as _audit  # noqa: PLC0415
        mode = request.args.get("mode", "highlight")
        if mode not in ("highlight", "verbose"):
            return jsonify({"error": "mode must be 'highlight' or 'verbose'"}), 400
        try:
            limit = max(1, min(int(request.args.get("limit", 20)), 100))
        except ValueError:
            limit = 20
        events = _audit.recent_events(limit=limit, mode=mode)
        return jsonify({
            "events": events,
            "mode": mode,
            "limit": limit,
            "count": len(events),
        })

    @app.route("/api/dashboard/snapshot", methods=["GET"])
    def dashboard_snapshot():
        """Consolidated dashboard snapshot — state + counts + recent activity.

        Perf budget: <500ms warm, <2s cold (operator-mandate Q7).
        All sub-queries best-effort with try/except → degrade to safe defaults.
        Daemon health checks parallelizable via concurrent.futures (kept
        sequential here since each curl has 1.5s timeout — total 4s worst-case;
        switch to ThreadPool only if perf gate fails).
        """
        import time as _time  # noqa: PLC0415
        t0 = _time.monotonic()
        repo_root = Path(__file__).parents[2]

        def _ping(url: str, timeout: float = 1.5) -> dict:
            try:
                r = requests.get(url, timeout=timeout)
                return {"up": r.status_code < 500, "code": r.status_code, "latency_ms": int(r.elapsed.total_seconds() * 1000)}
            except Exception:
                return {"up": False, "code": None, "latency_ms": None}

        daemons = {
            "flask": {"up": True, "code": 200, "latency_ms": 0},
            "llm_gateway": _ping(f"{GATEWAY_URL}/health"),
            "mascot_ws": _ping(f"{MASCOT_REST_URL}/health" if MASCOT_REST_URL else "http://localhost:9876/"),
            "chromadb": {"up": False, "code": None, "latency_ms": None},
            "discord": _detect_discord_bot(),
        }
        try:
            client = _chroma_client()
            client.heartbeat()
            daemons["chromadb"] = {"up": True, "code": 200, "latency_ms": 0}
        except Exception as exc:
            logger.warning("dashboard_snapshot: chromadb heartbeat failed: %s", exc)

        chars_db = 0
        try:
            chars_db = len(list_chars())
        except Exception as exc:
            logger.warning("dashboard_snapshot: chars_db query failed: %s", exc)
        chars_yaml = len(list((repo_root / "characters").rglob("*.yaml"))) if (repo_root / "characters").exists() else 0
        chars_archive = max(0, chars_yaml - chars_db)

        scenes_disk = len(list((repo_root / "scenes").rglob("*.md"))) if (repo_root / "scenes").exists() else 0
        scenes_db = 0
        try:
            client = _chroma_client()
            col = client.get_or_create_collection("calliope_scenes")
            scenes_db = col.count()
        except Exception:
            pass

        arcs = 0
        try:
            from app.calliope_shell.plot_arc import list_arcs  # noqa: PLC0415
            arcs = len(list_arcs())
        except Exception:
            pass

        lore_disk = len(list((repo_root / "lore").rglob("*.md"))) if (repo_root / "lore").exists() else 0

        messages_db = 0
        try:
            client = _chroma_client()
            col = client.get_or_create_collection("calliope_messages")
            messages_db = col.count()
        except Exception:
            pass

        # Active LLM provider — reflects current process state, toggleable
        # via POST /api/dashboard/llm_routing (Q3 operator decision).
        llm_routing = {
            "active_provider": _llm_routing_state["provider"],
            "active_model": _llm_routing_state["model"],
            "uncensored_available": True,
            "uncensored_provider": _UNCENSORED_PROFILE["provider"],
            "uncensored_active": _llm_routing_state["uncensored"],
        }

        # Recent activity from audit_trail (Sprint C3 — highlight subset).
        try:
            from app.calliope_shell import audit_trail as _audit  # noqa: PLC0415
            recent_activity = _audit.recent_events(limit=5, mode="highlight")
        except Exception:
            recent_activity = []

        elapsed_ms = int((_time.monotonic() - t0) * 1000)
        return jsonify({
            "daemons": daemons,
            "counts": {
                "chars": {"active": chars_db, "archive": chars_archive, "total_yaml": chars_yaml},
                "scenes": {"db": scenes_db, "disk": scenes_disk},
                "arcs": arcs,
                "lore_disk": lore_disk,
                "messages_indexed": messages_db,
            },
            "llm_routing": llm_routing,
            "recent_activity": recent_activity,
            "snapshot_latency_ms": elapsed_ms,
            "snapshot_taken_at": int(_time.time()),
        })

    @app.route("/api/dashboard/counts", methods=["GET"])
    def dashboard_counts():
        """Aggregate knowledge-base counts for landing dashboard widgets.

        Returns chars (DB + disk), scenes (DB + disk), arcs, lore docs.
        Each subquery is best-effort: failures degrade to 0, never break the
        endpoint (dashboard is informational, not transactional).
        """
        repo_root = Path(__file__).parents[2]

        chars_db = 0
        try:
            chars_db = len(list_chars())
        except Exception as exc:
            logger.warning("dashboard_counts: chars_db query failed: %s", exc)
        chars_yaml = len(list((repo_root / "characters").rglob("*.yaml"))) if (repo_root / "characters").exists() else 0

        scenes_disk = len(list((repo_root / "scenes").rglob("*.md"))) if (repo_root / "scenes").exists() else 0
        scenes_db = 0
        try:
            client = _chroma_client()
            col = client.get_or_create_collection("calliope_scenes")
            scenes_db = col.count()
        except Exception as exc:
            logger.warning("dashboard_counts: scenes_db query failed: %s", exc)

        arcs = 0
        try:
            from app.calliope_shell.plot_arc import list_arcs  # noqa: PLC0415
            arcs = len(list_arcs())
        except Exception as exc:
            logger.warning("dashboard_counts: arcs query failed: %s", exc)

        lore_disk = len(list((repo_root / "lore").rglob("*.md"))) if (repo_root / "lore").exists() else 0

        return jsonify({
            "chars": {"db": chars_db, "yaml": chars_yaml},
            "scenes": {"db": scenes_db, "disk": scenes_disk},
            "arcs": arcs,
            "lore_disk": lore_disk,
        })

    # ── Mascot routes ─────────────────────────────────────────────────────────

    @app.route("/api/mascot/state", methods=["GET"])
    def mascot_state_get():
        return jsonify({**_mascot_state, "ws_url": MASCOT_WS_URL})

    @app.route("/api/mascot/state", methods=["POST"])
    def mascot_state_post():
        global _mascot_state
        body = request.get_json(silent=True) or {}
        emotion = body.get("emotion", "neutral")
        intensity = float(body.get("intensity", 1.0))
        scene_id = body.get("scene_id")
        _mascot_state = {"emotion": emotion, "intensity": intensity, "scene_id": scene_id}
        try:
            resp = requests.post(
                f"{MASCOT_REST_URL}/event/emotion",
                json={"emotion": emotion},
                timeout=2,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("mascot WS relay failed (non-fatal): %s", exc)
        return jsonify({"status": "ok", "emotion": emotion})

    @app.route("/api/mascot/emotion_map", methods=["GET"])
    def mascot_emotion_map():
        return jsonify(_load_emotion_map())

    # ── Translate route ───────────────────────────────────────────────────────

    @app.route("/api/translate", methods=["POST"])
    def translate():
        body = request.get_json(silent=True) or {}
        text = body.get("text", "").strip()
        direction = body.get("direction", "IT_to_EN")
        context = body.get("context", "fantasy_rp")

        if not text:
            return jsonify({"error": "text is required"}), 400
        if direction not in _VALID_DIRECTIONS:
            return jsonify({"error": f"direction must be one of {sorted(_VALID_DIRECTIONS)}"}), 400

        if direction == "IT_to_EN":
            if context == "fantasy_rp":
                system = (
                    "You are a literary translator specializing in fantasy roleplay. "
                    "Translate Italian text to English preserving the tone, style, and fantasy vocabulary. "
                    "Keep character names, place names, and fantasy terms unchanged. "
                    "Output ONLY the translation, no explanations."
                )
            else:
                system = "Translate Italian to English accurately. Output ONLY the translation."
            prompt = f"Translate to English:\n\n{text}"
        else:
            if context == "fantasy_rp":
                system = (
                    "You are a literary translator specializing in fantasy roleplay. "
                    "Translate English text to Italian preserving the tone, style, and fantasy vocabulary. "
                    "Keep character names, place names, and fantasy terms unchanged. "
                    "Output ONLY the translation, no explanations."
                )
            else:
                system = "Translate English to Italian accurately. Output ONLY the translation."
            prompt = f"Translate to Italian:\n\n{text}"

        try:
            resp = requests.post(
                f"{GATEWAY_URL}/llm_ask",
                json={
                    "provider": "groq",
                    "model": "llama-3.3-70b-versatile",
                    "prompt": prompt,
                    "system": system,
                    "temperature": 0.3,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            translation = data.get("result") or data.get("text") or data.get("content", "")
            # Audit hook (Sprint C2).
            try:
                from app.calliope_shell import audit_trail as _audit  # noqa: PLC0415
                _audit.log_event(
                    "translate.run",
                    subject=direction,
                    detail=text[:120],
                    metadata={"in_chars": len(text), "out_chars": len(translation)},
                )
            except Exception:
                pass
            return jsonify({"translation": translation, "model_used": "groq/llama-3.3-70b-versatile"})
        except requests.exceptions.ConnectionError:
            return jsonify({"error": "LLM gateway not available", "code": "gateway_down"}), 503
        except requests.exceptions.Timeout:
            return jsonify({"error": "LLM gateway timeout"}), 503
        except Exception as exc:
            logger.warning("translate request failed: %s", exc)
            return jsonify({"error": "Translation failed", "detail": str(exc)}), 503

    # ── Char memory routes ────────────────────────────────────────────────────

    @app.route("/api/chars", methods=["GET"])
    def chars_list():
        return jsonify(list_chars())

    @app.route("/api/chars", methods=["POST"])
    def chars_upsert():
        body = request.get_json(silent=True) or {}
        name = body.get("name", "").strip()
        if not name:
            return jsonify({"error": "name is required"}), 400
        upsert_char(
            name,
            traits=body.get("traits"),
            last_action=body.get("last_action"),
            relationships=body.get("relationships"),
            last_scene_id=body.get("last_scene_id"),
        )
        return jsonify({"status": "ok", "name": name})

    @app.route("/api/chars/<name>", methods=["GET"])
    def chars_get(name: str):
        char = get_char(name)
        if char is None:
            return jsonify({"error": "char not found"}), 404
        return jsonify(char)

    @app.route("/api/chars/<name>/memory", methods=["GET"])
    def chars_memory(name: str):
        results = {"name": name, "snippets": [], "source": "chromadb"}
        try:
            client = _chroma_client()
            col = client.get_collection("calliope_messages")
            query_result = col.query(query_texts=[name], n_results=5)
            docs = query_result.get("documents", [[]])[0]
            dists = query_result.get("distances", [[]])[0]
            results["snippets"] = [
                {"text": doc[:200], "distance": round(dist, 4)}
                for doc, dist in zip(docs, dists)
            ]
        except Exception as exc:
            logger.warning("ChromaDB recall failed for %s (non-fatal): %s", name, exc)
            results["source"] = "unavailable"
            results["error"] = str(exc)

        char = get_char(name)
        if char:
            results["char_state"] = char
        return jsonify(results)

    # ── Char memory tools routes ──────────────────────────────────────────────

    @app.route("/api/char/memory_append", methods=["POST"])
    def char_action_append():
        body = request.get_json(silent=True) or {}
        char = body.get("char", "").strip()
        fact = body.get("fact", "").strip()
        scope = body.get("scope", "L1")
        if not char or not fact:
            return jsonify({"error": "char and fact are required"}), 400
        result = char_memory_append(char, fact, scope=scope)
        status = 200 if result.get("success") else 400
        return jsonify(result), status

    @app.route("/api/char/memory_replace", methods=["POST"])
    def char_action_replace():
        body = request.get_json(silent=True) or {}
        char = body.get("char", "").strip()
        old_fact = body.get("old_fact", "").strip()
        new_fact = body.get("new_fact", "").strip()
        scope = body.get("scope", "L1")
        approved = bool(body.get("approved", False))
        if not char or not old_fact or not new_fact:
            return jsonify({"error": "char, old_fact, new_fact are required"}), 400
        result = char_memory_replace(char, old_fact, new_fact, scope=scope, approved=approved)
        if result.get("requires_approval"):
            return jsonify(result), 202
        status = 200 if result.get("success") else 400
        return jsonify(result), status

    @app.route("/api/char/recall", methods=["POST"])
    def char_action_recall():
        body = request.get_json(silent=True) or {}
        char = body.get("char", "").strip()
        query = body.get("query", "").strip()
        top_k = int(body.get("top_k", 5))
        if not char or not query:
            return jsonify({"error": "char and query are required"}), 400
        result = char_memory_recall(char, query, top_k=top_k)
        return jsonify(result)

    @app.route("/api/char/<name>/facts", methods=["GET"])
    def char_facts_list(name: str):
        scope = request.args.get("scope")
        result = char_memory_list_facts(name, scope=scope)
        return jsonify(result)

    # ── Scene variant routes ──────────────────────────────────────────────────

    @app.route("/api/scene/refine", methods=["POST"])
    def scene_refine():
        import difflib  # noqa: PLC0415

        body = request.get_json(silent=True) or {}
        scene_text: str = body.get("scene_text") or ""
        scene_file_path: str = body.get("scene_file_path") or ""
        feedback: str = body.get("feedback", "").strip()
        auto_lint: bool = bool(body.get("auto_lint", False))

        if not scene_text and scene_file_path:
            try:
                scene_text = _safe_read_scene_file(scene_file_path)
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400
            except Exception as exc:
                return jsonify({"error": f"Cannot read file: {exc}"}), 400

        if not scene_text:
            return jsonify({"error": "scene_text or scene_file_path is required"}), 400
        if not feedback:
            return jsonify({"error": "feedback is required"}), 400

        feedback = feedback[:2000]
        refine_prompt = (
            f"Original scene:\n{scene_text}\n\n"
            f"Operator feedback: {feedback}\n\n"
            "Rewrite the scene applying the feedback. Preserve key narrative beats. "
            "Be concise and direct."
        )

        try:
            resp = requests.post(
                f"{GATEWAY_URL}/llm_ask",
                json={"provider": "groq", "model": "llama-3.3-70b-versatile", "prompt": refine_prompt},
                timeout=45,
            )
            resp.raise_for_status()
            data = resp.json()
            refined_text: str = data.get("content") or data.get("result") or ""
        except Exception as exc:
            logger.warning("scene_refine gateway call failed: %s", exc)
            return jsonify({"error": "LLM gateway unavailable", "detail": str(exc)}), 503

        lint_findings: list = []
        if auto_lint:
            try:
                import sys as _sys  # noqa: PLC0415
                _sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
                from style_filter import filter_response as _fr  # noqa: PLC0415
                refined_text, _hits = _fr(refined_text, severity_threshold="HIGH")
                lint_findings = [h["pattern"] for h in _hits if h.get("action") == "stripped"]
            except Exception as exc:
                logger.warning("auto-lint in refine route failed (non-fatal): %s", exc)

        # Simple line-diff for UI delta view
        orig_lines = scene_text.splitlines(keepends=True)
        ref_lines = refined_text.splitlines(keepends=True)
        diff_html = "".join(difflib.unified_diff(orig_lines, ref_lines, lineterm=""))

        # Audit hook (Sprint C2).
        try:
            from app.calliope_shell import audit_trail as _audit  # noqa: PLC0415
            _audit.log_event(
                "scene.refine",
                subject=scene_file_path or "inline_text",
                detail=feedback[:200],
                metadata={"auto_lint": auto_lint, "lint_findings_count": len(lint_findings)},
            )
        except Exception:
            pass

        return jsonify({
            "refined_text": refined_text,
            "diff": diff_html,
            "lint_findings": lint_findings,
            "auto_lint_applied": auto_lint,
        })

    @app.route("/api/scene/variants", methods=["POST"])
    def scene_variants():
        import sys as _sys  # noqa: PLC0415
        _sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
        from generate_scene import generate_variants, DEFAULT_STYLE_HINTS  # noqa: PLC0415,F401
        from route_scene import DEFAULT_CONFIG, load_config, route_scene  # noqa: PLC0415,F401

        body = request.get_json(silent=True) or {}
        prompt = body.get("prompt", "").strip()
        scene_type = body.get("scene_type", "action_combat")
        n_variants = min(int(body.get("n_variants", 3)), 5)
        style_hints = body.get("style_hints") or None

        if not prompt:
            return jsonify({"error": "prompt is required"}), 400

        try:
            config = load_config("data/llm_routing_config.yaml")
        except Exception:
            config = DEFAULT_CONFIG

        try:
            from route_scene import route_scene as _rs  # noqa: PLC0415
            nsfw_score = {"nudity_explicit": 0, "violence_gore": 0, "non_consent": 0, "minors_adjacent": 0}
            decision = _rs(scene_type, nsfw_score, "low", config)
            tier_name = decision["tier"]
            provider = decision["provider"]
        except Exception as exc:
            logger.warning("route_scene failed: %s — using default", exc)
            tier_name = "cerebras_workhorse"
            provider = "cerebras"

        try:
            variants = generate_variants(
                prompt=prompt,
                scene_type=scene_type,
                n_variants=n_variants,
                style_hints=style_hints,
                config=config,
                gateway_url=GATEWAY_URL,
                ollama_url="http://localhost:11434",
                tier_name=tier_name,
            )
        except Exception as exc:
            logger.warning("generate_variants failed: %s", exc)
            return jsonify({"error": str(exc)}), 503

        # Write variants file to tmp
        import tempfile  # noqa: PLC0415
        from generate_scene import _write_variants_file  # noqa: PLC0415
        from datetime import datetime as _dt  # noqa: PLC0415
        tmp_path = Path(tempfile.mktemp(suffix=".variants.md", prefix="calliope_"))
        _write_variants_file(
            tmp_path, variants, scene_type, tier_name, provider,
            _dt.now().isoformat(timespec="seconds"),
        )

        # Audit hook (Sprint C2).
        try:
            from app.calliope_shell import audit_trail as _audit  # noqa: PLC0415
            _audit.log_event(
                "scene.variants_generated",
                subject=scene_type,
                detail=f"n={len(variants)} prompt='{prompt[:80]}'",
                metadata={"tier": tier_name, "provider": provider, "n": len(variants)},
            )
        except Exception:
            pass

        return jsonify({
            "variants": [
                {"index": i + 1, "style": v["style"], "text": v["text"], "latency_ms": v["latency_ms"]}
                for i, v in enumerate(variants)
            ],
            "variants_file_path": str(tmp_path),
            "n": len(variants),
        })

    @app.route("/api/scene/blend", methods=["POST"])
    def scene_blend():
        import sys as _sys  # noqa: PLC0415
        _sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
        from blend_scene import parse_variants_file, blend_variants, parse_blend_spec  # noqa: PLC0415
        import tempfile  # noqa: PLC0415

        body = request.get_json(silent=True) or {}
        variants_file_path = body.get("variants_file_path", "").strip()
        blend_indices = body.get("blend_indices", [1, 2])
        hint = body.get("hint") or None

        if not variants_file_path:
            return jsonify({"error": "variants_file_path is required"}), 400

        try:
            vpath = _safe_variants_path(variants_file_path)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        if not vpath.exists():
            return jsonify({"error": f"variants file not found: {variants_file_path}"}), 404

        try:
            content = vpath.read_text(encoding="utf-8")
            variants = parse_variants_file(content)
            if not variants:
                return jsonify({"error": "no variants parsed from file"}), 400

            if isinstance(blend_indices, str):
                indices = parse_blend_spec(blend_indices)
            else:
                indices = [int(i) for i in blend_indices]

            blended, latency_ms = blend_variants(
                variants, indices, hint=hint, gateway_url=GATEWAY_URL,
            )
        except Exception as exc:
            logger.warning("scene_blend failed: %s", exc)
            return jsonify({"error": str(exc)}), 503

        out_path = Path(tempfile.mktemp(suffix=".blend.md", prefix="calliope_"))
        from blend_scene import write_blended_output  # noqa: PLC0415
        write_blended_output(out_path, blended, indices, hint, latency_ms, vpath)

        # Audit hook (Sprint C2).
        try:
            from app.calliope_shell import audit_trail as _audit  # noqa: PLC0415
            _audit.log_event(
                "scene.blend",
                subject=str(vpath.name),
                detail=f"indices={indices} latency={latency_ms}ms",
                metadata={"blend_indices": indices, "latency_ms": latency_ms},
            )
        except Exception:
            pass

        return jsonify({
            "blended_text": blended,
            "output_path": str(out_path),
            "latency_ms": latency_ms,
            "blend_indices": indices,
        })

    # ── Plot Arc routes ───────────────────────────────────────────────────────

    from app.calliope_shell import plot_arc as _pa  # noqa: PLC0415
    _pa.init_db()
    # Sprint C1: audit_trail table init at app startup so log_event() writes
    # land in the DB even before any other code path triggers init.
    from app.calliope_shell import audit_trail as _audit_init  # noqa: PLC0415
    _audit_init.init_db()

    @app.route("/api/arc", methods=["GET"])
    def arc_list():
        status = request.args.get("status")
        return jsonify(_pa.list_arcs(status=status))

    @app.route("/api/arc/<arc_id>", methods=["GET"])
    def arc_get(arc_id: str):
        arc = _pa.get_arc(arc_id)
        if arc is None:
            return jsonify({"error": "arc not found"}), 404
        return jsonify(arc)

    @app.route("/api/arc", methods=["POST"])
    def arc_create():
        body = request.get_json(silent=True) or {}
        arc_id = body.get("arc_id", "").strip()
        title = body.get("title", "").strip()
        chars = body.get("chars", [])
        if not arc_id or not title:
            return jsonify({"error": "arc_id and title are required"}), 400
        arc = _pa.create_arc(arc_id, title, chars)
        return jsonify(arc), 201

    @app.route("/api/arc/<arc_id>/append", methods=["POST"])
    def arc_append(arc_id: str):
        body = request.get_json(silent=True) or {}
        scene_md_path = body.get("scene_md_path", "").strip()
        scene_summary = body.get("scene_summary")
        if not scene_md_path:
            return jsonify({"error": "scene_md_path is required"}), 400
        result = _pa.append_scene(arc_id, scene_md_path, scene_summary)
        if not result:
            return jsonify({"error": "append_scene failed (file not found or arc missing)"}), 400
        return jsonify(result)

    @app.route("/api/arc/<arc_id>/summary", methods=["POST"])
    def arc_summary(arc_id: str):
        summary = _pa.regenerate_summary(arc_id)
        return jsonify({"arc_id": arc_id, "summary": summary})

    @app.route("/api/arc/<arc_id>/threads", methods=["GET"])
    def arc_threads(arc_id: str):
        threads = _pa.detect_open_threads(arc_id)
        return jsonify({"arc_id": arc_id, "threads": threads})

    @app.route("/api/arc/<arc_id>/continue", methods=["POST"])
    def arc_continue(arc_id: str):
        body = request.get_json(silent=True) or {}
        hint = body.get("hint")
        result = _pa.propose_next_scene(arc_id, hint=hint)
        if not result:
            return jsonify({"error": "propose_next_scene failed"}), 503
        return jsonify(result)

    @app.route("/api/arc/search", methods=["POST"])
    def arc_search():
        body = request.get_json(silent=True) or {}
        query = body.get("query", "").strip()
        if not query:
            return jsonify({"error": "query is required"}), 400
        results = _pa.search_arcs_by_topic(query)
        return jsonify({"results": results})

    # ── Draft generation (legacy FE-4 routes removed — see WI_FRONTEND_DB_MIGRATION) ──

    def _parse_scene_yaml(path: Path) -> dict:
        """Parse scene YAML, return flat dict with key fields."""
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if not isinstance(raw, dict):
                return {}
            return {
                "scene_id": raw.get("scene_id", path.stem),
                "title": raw.get("title", ""),
                "status": raw.get("status", "draft"),
                "summary": (raw.get("summary") or "")[:200],
                "participants": raw.get("participants", []),
                "date_started": raw.get("date_started", ""),
                "last_active": raw.get("last_active", ""),
                "message_count": raw.get("message_count", 0),
                "first_msg_excerpt": (raw.get("first_msg_excerpt") or "")[:120].strip(),
                "last_msg_excerpt": (raw.get("last_msg_excerpt") or "")[:120].strip(),
                "operator_notes": raw.get("operator_notes"),
            }
        except Exception as exc:
            logger.warning("parse_scene_yaml %s: %s", path.name, exc)
            return {}


    @app.route("/api/messages/next", methods=["POST"])
    def messages_next():
        """Generate next RP message given scene + char context. Gap C."""
        body = request.get_json(silent=True) or {}
        scene_id = body.get("scene_id", "").strip()
        char = body.get("char", "").strip()
        last_msg = body.get("last_msg", "").strip()
        context_hint = body.get("context_hint", "").strip()
        persist = bool(body.get("persist", False))

        if not char:
            return jsonify({"error": "char is required"}), 400

        # Build context from char_memory
        from app.calliope_shell.char_memory import retrieve_multi_signal  # noqa: PLC0415
        char_facts = []
        if char and last_msg:
            try:
                hits = retrieve_multi_signal(char, last_msg, top_k=3)
                char_facts = [h["fact_text"] for h in hits[:3]]
            except Exception:
                pass
        # ChromaDB char-grounding (GO Step 1b): profilo char da .chroma_calliope (by-slug)
        try:
            from app.calliope_shell.char_grounding import retrieve_char_grounding  # noqa: PLC0415
            char_facts.extend(retrieve_char_grounding(char))
        except Exception:
            pass

        # Build scene context — DB-FIRST con fallback flat-YAML (VG-1b, chiude F1).
        # Prima costruiva il contesto col glob _SCENES_DIR inline (il draft-gen non vedeva
        # mai il DB scene-as-chat). Ora passa per resolve_scene_context.
        scene_ctx = resolve_scene_context(scene_id, scenes_dir=_SCENES_DIR) if scene_id else ""

        # Compose prompt
        prompt_parts = [
            f"You are {char}, a character in a fantasy RP.",
        ]
        if scene_ctx:
            prompt_parts.append(f"\n{scene_ctx}")
        if char_facts:
            prompt_parts.append(f"\nKnown facts about {char}: {'; '.join(char_facts)}")
        if last_msg:
            prompt_parts.append(f"\nLast message in scene:\n{last_msg}")
        if context_hint:
            prompt_parts.append(f"\nDirection hint: {context_hint}")
        prompt_parts.append(f"\nWrite {char}'s next message (2-4 sentences, in character, in English).")
        full_prompt = "\n".join(prompt_parts)

        try:
            resp = requests.post(
                f"{GATEWAY_URL}/llm_ask",
                json={
                    "provider": "groq",
                    "model": "llama-3.3-70b-versatile",
                    "prompt": full_prompt,
                    "temperature": 0.8,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            next_msg = data.get("result") or data.get("text") or data.get("content", "")
            if persist and scene_id:
                try:
                    from app.db import get_db as _get_db  # noqa: PLC0415
                    from app.db.messages import add_message as _add_message  # noqa: PLC0415
                    _pconn = _get_db()
                    _add_message(_pconn, scene_id=scene_id, author_name=char, content_original=next_msg)
                    _pconn.commit()
                    _pconn.close()
                except Exception as _exc:
                    logger.warning("persist next_msg failed: %s", _exc)
            # Audit hook (Sprint C2).
            try:
                from app.calliope_shell import audit_trail as _audit  # noqa: PLC0415
                _audit.log_event(
                    "scene.next_msg",
                    subject=scene_id,
                    detail=f"{char}: {next_msg[:120]}",
                    metadata={"char": char, "ctx_facts": len(char_facts), "out_chars": len(next_msg)},
                )
            except Exception:
                pass
            return jsonify({
                "next_msg": next_msg,
                "char": char,
                "scene_id": scene_id,
                "context_used": {
                    "char_facts": len(char_facts),
                    "scene_context": bool(scene_ctx),
                    "last_msg": bool(last_msg),
                },
            })
        except requests.exceptions.ConnectionError:
            return jsonify({"error": "LLM gateway not available", "code": "gateway_down"}), 503
        except Exception as exc:
            logger.warning("messages_next failed: %s", exc)
            return jsonify({"error": str(exc)}), 503

    # ── Draft generation (VISION core feature) ────────────────────────────────

    @app.route("/api/draft", methods=["POST"])
    def draft_scene():
        body = request.get_json(silent=True) or {}
        scene_id = body.get("scene_id", "").strip()
        intent_it = body.get("intent_it", "").strip()
        char_focus = body.get("char_focus", "").strip()
        style_hints = body.get("style_hints", "")
        persist = bool(body.get("persist", False))

        if not intent_it:
            return jsonify({"error": "intent_it is required"}), 400

        # DB-FIRST con fallback flat-YAML (VG-1b, chiude F1) — non più glob inline per scene_ctx.
        scene_ctx = resolve_scene_context(scene_id, scenes_dir=_SCENES_DIR) if scene_id else ""
        # participants: DB-FIRST via list_characters_in_scene, fallback YAML glob.
        participants = []
        if scene_id:
            try:
                from app.db import get_db as _get_db  # noqa: PLC0415
                from app.db.characters import list_characters_in_scene as _list_chars_scene  # noqa: PLC0415
                _conn = _get_db()
                _db_rows = _list_chars_scene(_conn, scene_id)
                _conn.close()
                participants = [r["name"] for r in _db_rows]
            except Exception:
                pass
            if not participants:
                for p in _SCENES_DIR.glob("*.yaml"):
                    if scene_id in p.stem:
                        d = _parse_scene_yaml(p)
                        if d:
                            participants = d.get("participants", [])
                        break

        char_sheets = _load_char_sheets(
            [char_focus] if char_focus else participants[:5]
        )

        char_facts = []
        focus_names = [char_focus] if char_focus else participants[:3]
        for cn in focus_names:
            if not cn:
                continue
            try:
                from app.calliope_shell.char_memory import retrieve_multi_signal  # noqa: PLC0415
                hits = retrieve_multi_signal(cn, intent_it, top_k=3)
                char_facts.extend(
                    f"{cn}: {h['fact_text']}" for h in hits[:2]
                )
            except Exception:
                pass
            # ChromaDB char-grounding (GO Step 1b): profilo char da .chroma_calliope (by-slug)
            try:
                from app.calliope_shell.char_grounding import retrieve_char_grounding  # noqa: PLC0415
                char_facts.extend(f"{cn}: {g}" for g in retrieve_char_grounding(cn))
            except Exception:
                pass

        lore_snippets = _search_lore(intent_it, n=3)

        sheets_text = ""
        for s in char_sheets:
            sp = s.get("speech_pattern", {})
            sheets_text += (
                f"\n[{s['name']}] {s.get('race','')} {s.get('class','')}\n"
                f"Traits: {', '.join(s.get('traits', []))}\n"
                f"Backstory: {s.get('backstory', '')}\n"
                f"Speech: vocab={sp.get('vocabulary','')}, "
                f"pov={sp.get('pov','')}, notes={sp.get('notes','')}\n"
            )

        prompt_parts = [
            "You are a literary fantasy RP writer producing high-quality English prose.",
            "Write a scene draft based on the operator's intent (given in Italian).",
            "Preserve character voice, use vivid sensory details, and maintain narrative continuity.",
        ]
        if scene_ctx:
            prompt_parts.append(f"\n--- SCENE CONTEXT ---\n{scene_ctx}")
        if sheets_text:
            prompt_parts.append(f"\n--- CHARACTERS ---{sheets_text}")
        if char_facts:
            prompt_parts.append("\n--- CHARACTER MEMORY ---\n" + "\n".join(char_facts))
        if lore_snippets:
            prompt_parts.append("\n--- LORE ---\n" + "\n".join(lore_snippets))
        if style_hints:
            prompt_parts.append(f"\n--- STYLE ---\n{style_hints}")
        prompt_parts.append(f"\n--- OPERATOR INTENT (Italian) ---\n{intent_it}")
        prompt_parts.append(
            "\nWrite the draft scene in English. "
            "Be literary and evocative. 200-500 words."
        )

        full_prompt = "\n".join(prompt_parts)

        try:
            resp = requests.post(
                f"{GATEWAY_URL}/llm_code",
                json={
                    "provider": "cerebras",
                    "prompt": full_prompt,
                    "temperature": 0.7,
                    # zai-glm-4.7 è un reasoning-model: serve budget ampio o il reasoning
                    # esaurisce i token e la risposta non ha 'content' (era qwen-3-235b non-reasoning).
                    "max_tokens": 4096,
                },
                timeout=90,
            )
            resp.raise_for_status()
            data = resp.json()
            draft_text = data.get("result") or data.get("text") or data.get("content", "")
        except requests.exceptions.ConnectionError:
            return jsonify({"error": "LLM gateway not available", "code": "gateway_down"}), 503
        except Exception as exc:
            logger.warning("draft generation failed: %s", exc)
            return jsonify({"error": str(exc)}), 503

        if persist and scene_id:
            try:
                from app.db import get_db as _get_db  # noqa: PLC0415
                from app.db.messages import add_message as _add_message  # noqa: PLC0415
                _pconn = _get_db()
                _add_message(_pconn, scene_id=scene_id, author_name=char_focus, content_original=draft_text)
                _pconn.commit()
                _pconn.close()
            except Exception as _exc:
                logger.warning("persist draft failed: %s", _exc)

        lint_findings = []
        try:
            import sys as _sys  # noqa: PLC0415
            _sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
            from style_filter import filter_response as _fr  # noqa: PLC0415
            draft_text, hits = _fr(draft_text, severity_threshold="HIGH")
            lint_findings = [h["pattern"] for h in hits if h.get("action") == "stripped"]
        except Exception as exc:
            logger.warning("style_filter in draft route failed (non-fatal): %s", exc)

        try:
            from app.calliope_shell import audit_trail as _audit  # noqa: PLC0415
            _audit.log_event(
                "draft.generate",
                subject=scene_id or "no_scene",
                detail=intent_it[:200],
                metadata={
                    "char_focus": char_focus,
                    "chars_loaded": len(char_sheets),
                    "lore_hits": len(lore_snippets),
                    "char_facts": len(char_facts),
                    "out_chars": len(draft_text),
                    "lint_findings": len(lint_findings),
                },
            )
        except Exception:
            pass

        return jsonify({
            "draft_text": draft_text,
            "model_used": "cerebras/zai-glm-4.7",
            "context_used": {
                "scene": bool(scene_ctx),
                "char_sheets": len(char_sheets),
                "char_facts": len(char_facts),
                "lore_snippets": len(lore_snippets),
                "style_hints": bool(style_hints),
            },
            "lint_findings": lint_findings,
        })

    # ── Summarize (VISION CLI /summarize) ────────────────────────────────────

    @app.route("/api/summarize", methods=["POST"])
    def summarize():
        body = request.get_json(silent=True) or {}
        text = body.get("text", "").strip()
        max_length = min(int(body.get("max_length", 200)), 500)

        if not text:
            return jsonify({"error": "text is required"}), 400

        prompt = (
            f"Summarize the following roleplay / Discord conversation text.\n"
            f"Output a JSON object with two fields:\n"
            f"- \"summary\": a concise summary (max {max_length} words)\n"
            f"- \"key_facts\": a list of 3-7 key facts extracted (names, events, decisions, locations)\n\n"
            f"Text:\n{text[:5000]}\n\n"
            f"Respond ONLY with valid JSON, no markdown fences."
        )

        try:
            resp = requests.post(
                f"{GATEWAY_URL}/llm_ask",
                json={
                    "provider": "groq",
                    "model": "llama-3.3-70b-versatile",
                    "prompt": prompt,
                    "temperature": 0.2,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            raw_result = data.get("result") or data.get("text") or data.get("content", "")
        except requests.exceptions.ConnectionError:
            return jsonify({"error": "LLM gateway not available", "code": "gateway_down"}), 503
        except Exception as exc:
            logger.warning("summarize failed: %s", exc)
            return jsonify({"error": str(exc)}), 503

        import json as _json  # noqa: PLC0415
        summary = raw_result
        key_facts: list = []
        try:
            clean = raw_result.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
            parsed = _json.loads(clean)
            summary = parsed.get("summary", raw_result)
            key_facts = parsed.get("key_facts", [])
        except (_json.JSONDecodeError, Exception):
            pass

        try:
            from app.calliope_shell import audit_trail as _audit  # noqa: PLC0415
            _audit.log_event(
                "summarize.run",
                subject="paste",
                detail=text[:200],
                metadata={"in_chars": len(text), "key_facts": len(key_facts)},
            )
        except Exception:
            pass

        return jsonify({
            "summary": summary,
            "key_facts": key_facts,
            "word_count": len(summary.split()),
            "model_used": "groq/llama-3.3-70b-versatile",
        })

    # ── Scene revive (VISION §Scene long-tail persistence) ───────────────────

    @app.route("/api/scene/revive", methods=["POST"])
    def scene_revive():
        body = request.get_json(silent=True) or {}
        scene_id = body.get("scene_id", "").strip()

        if not scene_id:
            return jsonify({"error": "scene_id is required"}), 400

        scene_data = None
        for p in _SCENES_DIR.glob("*.yaml"):
            if scene_id in p.stem:
                scene_data = _parse_scene_yaml(p)
                if scene_data:
                    break

        if not scene_data:
            return jsonify({"error": "scene not found"}), 404

        participants = scene_data.get("participants", [])
        char_sheets = _load_char_sheets(participants[:5])

        char_facts = []
        for cn in participants[:3]:
            try:
                from app.calliope_shell.char_memory import retrieve_multi_signal  # noqa: PLC0415
                hits = retrieve_multi_signal(cn, scene_data.get("summary", cn), top_k=3)
                char_facts.extend(f"{cn}: {h['fact_text']}" for h in hits[:2])
            except Exception:
                pass

        recent_messages = []
        try:
            client = _chroma_client()
            col = client.get_collection("calliope_messages")
            query_text = f"{scene_data.get('title', scene_id)} {' '.join(participants[:3])}"
            results = col.query(query_texts=[query_text], n_results=5)
            recent_messages = [doc[:200] for doc in (results.get("documents", [[]])[0])]
        except Exception:
            pass

        lore_refs = _search_lore(
            f"{scene_data.get('title', '')} {scene_data.get('summary', '')}", n=3
        )

        revival_prompt = (
            f"A dormant RP scene is being revived after a long pause.\n"
            f"Scene: {scene_data.get('title', scene_id)}\n"
            f"Summary: {scene_data.get('summary', '')}\n"
            f"Participants: {', '.join(participants)}\n"
            f"Last excerpt: {scene_data.get('last_msg_excerpt', '')}\n"
        )
        if char_facts:
            revival_prompt += "\nCharacter memory:\n" + "\n".join(char_facts[:6])
        if recent_messages:
            revival_prompt += "\nRecent exchanges:\n" + "\n".join(recent_messages[:3])
        if scene_data.get("operator_notes"):
            revival_prompt += f"\nOperator notes: {scene_data['operator_notes']}"
        revival_prompt += (
            "\n\nWrite a brief revival summary (100-200 words): "
            "what was happening, where things left off, what each character was doing, "
            "and suggest 2-3 possible re-entry points for the scene."
        )

        suggested_reentry = ""
        try:
            resp = requests.post(
                f"{GATEWAY_URL}/llm_ask",
                json={
                    "provider": "groq",
                    "model": "llama-3.3-70b-versatile",
                    "prompt": revival_prompt,
                    "temperature": 0.5,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            suggested_reentry = data.get("result") or data.get("text") or data.get("content", "")
        except Exception as exc:
            logger.warning("scene_revive LLM call failed (non-fatal): %s", exc)
            suggested_reentry = "(LLM unavailable — manual review of context below)"

        try:
            from app.calliope_shell import audit_trail as _audit  # noqa: PLC0415
            _audit.log_event(
                "scene.revive",
                subject=scene_id,
                detail=scene_data.get("title", "")[:200],
                metadata={
                    "participants": len(participants),
                    "char_facts": len(char_facts),
                    "lore_refs": len(lore_refs),
                    "recent_msgs": len(recent_messages),
                },
            )
        except Exception:
            pass

        return jsonify({
            "scene_context": {
                "scene_id": scene_data.get("scene_id", scene_id),
                "title": scene_data.get("title", ""),
                "status": scene_data.get("status", ""),
                "summary": scene_data.get("summary", ""),
                "last_excerpt": scene_data.get("last_msg_excerpt", ""),
                "operator_notes": scene_data.get("operator_notes"),
            },
            "participants": [
                {"name": s["name"], "traits": s.get("traits", []), "race": s.get("race", "")}
                for s in char_sheets
            ],
            "char_facts": char_facts,
            "recent_messages": recent_messages,
            "lore_refs": lore_refs,
            "suggested_reentry": suggested_reentry,
            "model_used": "groq/llama-3.3-70b-versatile",
        })

    # ── Lore search (VISION §2 /lore search <query>) ───────────────────────

    @app.route("/api/lore/search", methods=["POST"])
    def lore_search():
        body = request.get_json(silent=True) or {}
        query = body.get("query", "").strip()
        n = min(int(body.get("n", 10)), 20)

        if not query:
            return jsonify({"error": "query is required"}), 400

        try:
            client = _chroma_client()
            col = client.get_collection("calliope_lore")
            results = col.query(query_texts=[query], n_results=n, include=["documents", "metadatas", "distances"])
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            dists = results.get("distances", [[]])[0]
            hits = [
                {
                    "text": doc,
                    "source": meta.get("source", ""),
                    "type": meta.get("type", ""),
                    "char": meta.get("char", ""),
                    "distance": round(dist, 4),
                }
                for doc, meta, dist in zip(docs, metas, dists)
            ]
        except Exception as exc:
            logger.warning("lore_search failed: %s", exc)
            return jsonify({"results": [], "count": 0, "error": str(exc)})

        try:
            from app.calliope_shell import audit_trail as _audit  # noqa: PLC0415
            _audit.log_event(
                "lore.search",
                subject=query[:100],
                detail=f"hits={len(hits)}",
                metadata={"query_len": len(query), "n": n, "hits": len(hits)},
            )
        except Exception:
            pass

        return jsonify({"results": hits, "count": len(hits), "query": query})

    # ── Lore coherence check (VISION calliope-lore-coherent) ─────────────────

    @app.route("/api/lore/check", methods=["POST"])
    def lore_check():
        body = request.get_json(silent=True) or {}
        text = body.get("text", "").strip()
        scene_id = body.get("scene_id", "").strip()

        if not text:
            return jsonify({"error": "text is required"}), 400

        search_query = text[:500]
        if scene_id:
            for p in _SCENES_DIR.glob("*.yaml"):
                if scene_id in p.stem:
                    d = _parse_scene_yaml(p)
                    if d:
                        search_query = f"{d.get('title', '')} {text[:300]}"
                    break

        lore_snippets = _search_lore(search_query, n=5)

        if not lore_snippets:
            try:
                from app.calliope_shell import audit_trail as _audit  # noqa: PLC0415
                _audit.log_event(
                    "lore.check", subject=scene_id or "inline",
                    detail="no lore found", metadata={"text_len": len(text)},
                )
            except Exception:
                pass
            return jsonify({
                "coherent": True,
                "issues": [],
                "checked_against": [],
                "note": "No lore documents found in ChromaDB to check against.",
            })

        review_prompt = (
            "You are a lore consistency checker for a fantasy RP world.\n"
            "Compare the DRAFT TEXT against the LORE REFERENCES below.\n"
            "Identify any contradictions, inconsistencies, or factual errors.\n\n"
            f"DRAFT TEXT:\n{text[:3000]}\n\n"
            f"LORE REFERENCES:\n" + "\n---\n".join(lore_snippets) + "\n\n"
            "Output a JSON object:\n"
            '- "coherent": true/false\n'
            '- "issues": [{\"severity\": \"warning\"|\"error\", \"description\": \"...\", \"lore_ref\": \"...\"}]\n'
            "If no issues found, set coherent=true and issues=[].\n"
            "Respond ONLY with valid JSON, no markdown fences."
        )

        try:
            resp = requests.post(
                f"{GATEWAY_URL}/llm_review",
                json={
                    "provider": "openrouter",
                    "prompt": review_prompt,
                    "temperature": 0.1,
                },
                timeout=45,
            )
            resp.raise_for_status()
            data = resp.json()
            raw_result = data.get("result") or data.get("text") or data.get("content", "")
        except requests.exceptions.ConnectionError:
            return jsonify({"error": "LLM gateway not available", "code": "gateway_down"}), 503
        except Exception as exc:
            logger.warning("lore_check failed: %s", exc)
            return jsonify({"error": str(exc)}), 503

        import json as _json  # noqa: PLC0415
        coherent = True
        issues: list = []
        try:
            clean = raw_result.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
            parsed = _json.loads(clean)
            coherent = parsed.get("coherent", True)
            issues = parsed.get("issues", [])
        except (_json.JSONDecodeError, Exception):
            issues = [{"severity": "warning", "description": "Could not parse LLM response", "lore_ref": ""}]
            coherent = False

        try:
            from app.calliope_shell import audit_trail as _audit  # noqa: PLC0415
            _audit.log_event(
                "lore.check",
                subject=scene_id or "inline",
                detail=f"coherent={coherent} issues={len(issues)}",
                metadata={"text_len": len(text), "lore_checked": len(lore_snippets), "issues": len(issues)},
            )
        except Exception:
            pass

        return jsonify({
            "coherent": coherent,
            "issues": issues,
            "checked_against": [s[:100] for s in lore_snippets],
            "model_used": "openrouter/deepseek-r1-0528",
        })

    return app, FLASK_PORT


app, FLASK_PORT = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(FLASK_PORT), debug=False)
