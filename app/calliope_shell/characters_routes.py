from flask import jsonify
from app.calliope_shell import characters_service


def register_character_routes(app):
    @app.route("/api/characters", methods=["GET"])
    def characters_list():
        return jsonify(characters_service.list_cards())

    @app.route("/api/characters/<stem>", methods=["GET"])
    def characters_get(stem):
        card = characters_service.get_card_v3(stem)
        if card is None:
            return jsonify({"error": "character not found"}), 404
        return jsonify(card)
