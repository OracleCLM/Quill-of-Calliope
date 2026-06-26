import re
import yaml
from pathlib import Path
from flask import jsonify, request, current_app
from app.calliope_shell import characters_service


def register_character_routes(app):
    @app.route("/api/characters", methods=["GET"])
    def characters_list():
        return jsonify(characters_service.list_cards())

    @app.route("/api/characters", methods=["POST"])
    def characters_create():
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name required"}), 400
        stem = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if not stem:
            return jsonify({"error": "invalid name"}), 400
        chars_path = characters_service._chars_dir()
        draft_path = chars_path / f"{stem}.draft.yaml"
        if draft_path.exists():
            return jsonify({"error": "already exists", "stem": stem}), 409
        kind = data.get("kind", "npc")
        card_data = {
            "name": name,
            "description": (data.get("description") or "").strip(),
            "personality": (data.get("personality") or "").strip(),
            "tags": [kind],
        }
        draft_path.write_text(yaml.dump(card_data, allow_unicode=True), encoding="utf-8")
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
