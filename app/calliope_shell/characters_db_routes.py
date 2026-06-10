from flask import jsonify, request
from app.db import get_db
from app.db import characters as db_chars

VALID_KINDS = {"operator", "player", "npc"}


def _conn(db_path):
    return get_db(db_path) if db_path else get_db()


def register_characters_db_routes(app, *, db_path: str) -> None:

    @app.route("/api/db/characters", methods=["GET"])
    def list_characters_db():
        conn = _conn(db_path)
        kind = request.args.get("kind")
        chars = db_chars.list_characters(conn, kind=kind)
        conn.close()
        return jsonify({"characters": [dict(c) for c in chars]}), 200

    @app.route("/api/db/characters", methods=["POST"])
    def add_character_db():
        data = request.get_json(silent=True) or {}
        name = data.get("name")
        if not name:
            return jsonify({"error": "name required"}), 400
        kind = data.get("kind", "npc")
        if kind not in VALID_KINDS:
            return jsonify({"error": "invalid kind"}), 400
        conn = _conn(db_path)
        char_id = db_chars.add_character(conn, name=name, kind=kind)
        conn.close()
        return jsonify({"id": char_id}), 201

    @app.route("/api/db/characters/<char_id>", methods=["GET"])
    def get_character_db(char_id):
        conn = _conn(db_path)
        char = db_chars.get_character(conn, char_id)
        conn.close()
        if char is None:
            return jsonify({"error": "not found"}), 404
        return jsonify(dict(char)), 200

    @app.route("/api/db/characters/<char_id>", methods=["PATCH"])
    def update_character_db(char_id):
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"error": "body required"}), 400

        name = data.get("name")
        kind = data.get("kind")
        image_path = data.get("image_path")

        if kind is not None and kind not in VALID_KINDS:
            return jsonify({"error": "invalid kind"}), 400

        conn = _conn(db_path)
        updated = db_chars.update_character(
            conn, char_id, name=name, kind=kind, image_path=image_path
        )
        conn.close()

        if updated:
            return jsonify({}), 200
        return jsonify({"error": "not found"}), 404

    @app.route("/api/db/characters/<char_id>", methods=["DELETE"])
    def delete_character_db(char_id):
        conn = _conn(db_path)
        if db_chars.delete_character(conn, char_id):
            conn.close()
            return "", 204
        conn.close()
        return jsonify({"error": "not found"}), 404
