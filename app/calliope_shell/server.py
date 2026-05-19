import logging
import os
from pathlib import Path

import chromadb
import requests
import yaml
from flask import Flask, jsonify, request, render_template

from app.calliope_shell.char_memory import get_char, list_chars, upsert_char

logger = logging.getLogger(__name__)

_mascot_state: dict = {"emotion": "neutral", "intensity": 1.0, "scene_id": None}

_CHROMA_PATH = str(Path(__file__).parents[2] / ".chroma_calliope")
_VALID_DIRECTIONS = {"IT_to_EN", "EN_to_IT"}


def _chroma_client():
    return chromadb.PersistentClient(path=_CHROMA_PATH)


def _load_emotion_map() -> dict:
    map_path = Path(__file__).parents[2] / "data" / "aurora_emotion_map.yaml"
    try:
        return yaml.safe_load(map_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        logger.warning("aurora_emotion_map.yaml load failed: %s", exc)
        return {}


def create_app():
    app = Flask(__name__)

    FLASK_PORT = os.getenv("FLASK_PORT", "5000")
    ST_URL = os.getenv("ST_URL", "http://localhost:8001")
    MASCOT_WS_URL = os.getenv("MASCOT_WS_URL", "ws://localhost:9876")
    MASCOT_REST_URL = os.getenv("MASCOT_REST_URL", "http://localhost:9876")
    GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8766")

    # ── Core routes ──────────────────────────────────────────────────────────

    @app.route("/")
    def index():
        return render_template("shell.html", ST_URL=ST_URL, MASCOT_WS_URL=MASCOT_WS_URL)

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

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

    return app, FLASK_PORT


app, FLASK_PORT = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(FLASK_PORT), debug=False)
