"""
Route DB-backed per le reazioni ai messaggi (scene_reactions).

Estratto da scenes_db_routes.py (refactor 2026-06-11: split del monolite per
ridurre il contesto-edit e sbloccare i modelli cost-zero su questa risorsa).
Registrato da server.py:create_app() via register_reactions_db_routes.
"""

from __future__ import annotations

from flask import jsonify, request

from app.db import get_db
from app.db import messages as db_messages
from app.db import reactions as db_reactions


def _conn(db_path):
    """Apre una connessione: db_path esplicito (test temp) o default produzione."""
    return get_db(db_path) if db_path else get_db()


def register_reactions_db_routes(app, db_path=None):
    """Registra gli endpoint reazioni sul Flask ``app``."""

    @app.route("/api/db/messages/<message_id>/reactions", methods=["GET"])
    def db_list_reactions(message_id):
        conn = _conn(db_path)
        data = db_reactions.list_reactions(conn, message_id=message_id)
        conn.close()
        return jsonify({"reactions": list(data)}), 200

    @app.route("/api/db/messages/<message_id>/reactions", methods=["POST"])
    def db_add_reaction(message_id):
        conn = _conn(db_path)
        body = request.get_json(force=True) or {}
        if "character_id" not in body:
            conn.close()
            return jsonify({"error": "missing character_id"}), 400
        if db_messages.get_message_by_id(conn, message_id) is None:
            conn.close()
            return jsonify({"error": "not found"}), 404
        rid = db_reactions.add_reaction(conn, message_id=message_id,
            character_id=body["character_id"], emoji=body.get("emoji", ""))
        conn.close()
        return jsonify({"id": rid}), 201

    @app.route(
        "/api/db/messages/<message_id>/reactions/<reaction_id>", methods=["DELETE"]
    )
    def db_delete_reaction(message_id, reaction_id):
        # WI-39: elimina una reazione da scene_reactions (id PK).
        conn = _conn(db_path)
        cur = conn.execute(
            "DELETE FROM scene_reactions WHERE id = ?", (reaction_id,)
        )
        conn.commit()
        conn.close()
        if cur.rowcount > 0:
            return "", 204
        return jsonify({"error": "not_found"}), 404
