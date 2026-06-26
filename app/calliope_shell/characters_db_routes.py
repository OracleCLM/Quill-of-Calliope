from flask import jsonify, request
from app.db import get_db
from app.db import characters as db_chars

VALID_KINDS = {"operator", "player", "npc"}


def _conn(db_path):
    return get_db(db_path) if db_path else get_db()


def register_characters_db_routes(app, *, db_path=None) -> None:

    @app.route("/api/db/characters", methods=["GET"])
    def list_characters_db():
        conn = _conn(db_path)
        kind = request.args.get("kind")
        name = request.args.get("name")
        chars = db_chars.list_characters(conn, kind=kind)
        conn.close()
        result = [dict(c) for c in chars]
        if name:
            nl = name.lower()
            result = [c for c in result if c.get("name", "").lower() == nl]
        return jsonify({"characters": result}), 200

    @app.route("/api/db/characters", methods=["POST"])
    def add_character_db():
        data = request.get_json(silent=True) or {}
        name = data.get("name")
        if not name:
            return jsonify({"error": "name required"}), 400
        kind = data.get("kind", "npc")
        if kind not in VALID_KINDS:
            return jsonify({"error": "invalid kind"}), 400
        card_json = data.get("card_json")  # stringa opaca (WI-47)
        conn = _conn(db_path)
        try:
            char_id = db_chars.add_character(
                conn, name=name, kind=kind, card_json=card_json
            )
        except ValueError as exc:
            # es. name > 255 caratteri (WI-55)
            conn.close()
            return jsonify({"error": str(exc)}), 400
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
        card_json = data.get("card_json")  # stringa opaca (WI-47)

        if kind is not None and kind not in VALID_KINDS:
            return jsonify({"error": "invalid kind"}), 400

        conn = _conn(db_path)
        updated = db_chars.update_character(
            conn, char_id, name=name, kind=kind, image_path=image_path,
            card_json=card_json,
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

    @app.route("/api/db/characters/<char_id>/scenes", methods=["GET"])
    def list_scenes_for_character(char_id):
        conn = _conn(db_path)
        cur = conn.execute(
            "SELECT s.id, s.title, s.location, sc.role FROM scenes s "
            "JOIN scene_characters sc ON sc.scene_id = s.id "
            "WHERE sc.character_id = ? ORDER BY s.updated_at DESC",
            (char_id,),
        )
        rows = [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]
        conn.close()
        return jsonify({"scenes": rows}), 200
