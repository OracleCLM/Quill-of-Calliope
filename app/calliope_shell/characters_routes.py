from pathlib import Path
from flask import jsonify, request, current_app
from app.calliope_shell import characters_service


def register_character_routes(app):
    @app.route("/api/characters", methods=["GET"])
    def characters_list():
        return jsonify(characters_service.list_cards())

    @app.route("/api/characters", methods=["POST"])
    def characters_create():
        body = request.get_json(silent=True) or {}
        name = (body.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name required"}), 400
        stem = characters_service.create_draft(name)
        return jsonify({"stem": stem, "name": name}), 201

    @app.route("/api/characters/<stem>", methods=["GET"])
    def characters_get(stem):
        card = characters_service.get_card_v3(stem)
        if card is None:
            return jsonify({"error": "character not found"}), 404
        return jsonify(card)

    @app.route("/api/characters/<stem>/image", methods=["POST"])
    def characters_upload_image(stem):
        if characters_service.get_card_v3(stem) is None:
            return jsonify({"error": "not found"}), 404
        f = request.files.get("image")
        if not f:
            return jsonify({"error": "missing image field"}), 400
        ext = Path(f.filename).suffix or ".png"
        dest = Path(current_app.static_folder) / "media" / "characters"
        dest.mkdir(parents=True, exist_ok=True)
        f.save(dest / f"{stem}{ext}")
        return jsonify({"image_path": f"media/characters/{stem}{ext}"}), 200
