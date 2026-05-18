import os

from flask import Flask, jsonify, render_template


def create_app():
    app = Flask(__name__)

    FLASK_PORT = os.getenv("FLASK_PORT", "5000")
    ST_URL = os.getenv("ST_URL", "http://localhost:8001")
    MASCOT_WS_URL = os.getenv("MASCOT_WS_URL", "ws://localhost:9876")

    @app.route("/")
    def index():
        return render_template("shell.html", ST_URL=ST_URL, MASCOT_WS_URL=MASCOT_WS_URL)

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.route("/api/mascot/state")
    def mascot_state():
        return jsonify({
            "state": "idle",
            "expression": "neutral",
            "ws_url": MASCOT_WS_URL,
        })

    return app, FLASK_PORT


app, FLASK_PORT = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(FLASK_PORT), debug=False)
