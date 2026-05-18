import logging
import os
from pathlib import Path

import requests
import yaml
from flask import Flask, jsonify, request, render_template


logger = logging.getLogger(__name__)

_mascot_state: dict = {"emotion": "neutral", "intensity": 1.0, "scene_id": None}


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

    @app.route("/")
    def index():
        return render_template("shell.html", ST_URL=ST_URL, MASCOT_WS_URL=MASCOT_WS_URL)

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

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

    return app, FLASK_PORT


app, FLASK_PORT = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(FLASK_PORT), debug=False)
