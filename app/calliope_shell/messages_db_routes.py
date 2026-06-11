"""
Route DB-backed per i messaggi indirizzati per id (/api/db/messages/<id>).

Estratto da scenes_db_routes.py (refactor 2026-06-11, slice 2: split del monolite
per ridurre il contesto-edit e sbloccare i modelli cost-zero su questa risorsa).
Registrato transitivamente da register_scenes_db_routes (backward-compat).
"""

from __future__ import annotations

from flask import jsonify, request

from app.db import get_db
from app.db import messages as db_messages


def _conn(db_path):
    """Apre una connessione: db_path esplicito (test temp) o default produzione."""
    return get_db(db_path) if db_path else get_db()


def register_messages_db_routes(app, db_path=None):
    """Registra gli endpoint messaggi-per-id sul Flask ``app``."""

    @app.route("/api/db/messages/<message_id>/position", methods=["PATCH"])
    def db_update_message_position(message_id):
        conn = _conn(db_path)
        body = request.get_json(force=True) or {}

        if "position" not in body:
            conn.close()
            return jsonify({"error": "bad_request"}), 400

        position = body["position"]
        if not isinstance(position, int):
            conn.close()
            return jsonify({"error": "bad_request"}), 400

        moved = db_messages.move_message(conn, message_id, position)
        conn.close()

        if not moved:
            return jsonify({"error": "not_found"}), 404

        return jsonify({}), 200

    @app.route("/api/db/messages/<message_id>", methods=["GET"])
    def db_get_message_by_id(message_id):
        conn = _conn(db_path)
        msg = db_messages.get_message_by_id(conn, message_id)
        conn.close()
        if msg is None:
            return jsonify({"error": "not_found"}), 404
        return jsonify(msg), 200

    @app.route("/api/db/messages/<message_id>", methods=["DELETE"])
    def db_delete_message(message_id):
        conn = _conn(db_path)
        if db_messages.delete_message(conn, message_id):
            conn.commit()
            conn.close()
            return "", 204
        conn.close()
        return jsonify({"error": "not_found"}), 404
