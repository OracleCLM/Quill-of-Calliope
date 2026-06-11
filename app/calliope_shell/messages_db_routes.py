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

    @app.route("/api/db/messages/<message_id>", methods=["PATCH"])
    def db_update_message(message_id):
        body = request.get_json(force=True) or {}
        content_original = body.get("content_original")
        author_name = body.get("author_name")
        if content_original is None and author_name is None:
            return jsonify({"error": "bad_request"}), 400
        conn = _conn(db_path)
        updated = db_messages.update_message(
            conn, message_id,
            content_original=content_original,
            author_name=author_name,
        )
        conn.close()
        if not updated:
            return jsonify({"error": "not_found"}), 404
        return jsonify({"id": message_id}), 200

    @app.route("/api/db/messages/<message_id>/move", methods=["POST"])
    def db_move_message_to_scene(message_id):
        body = request.get_json(force=True) or {}
        target_scene_id = body.get("target_scene_id")
        position = body.get("position")
        if target_scene_id is None or position is None:
            return jsonify({"error": "bad_request"}), 400
        conn = _conn(db_path)
        moved = db_messages.move_message_to_scene(
            conn, message_id, target_scene_id, position
        )
        conn.close()
        if not moved:
            return jsonify({"error": "not_found"}), 404
        return jsonify({}), 200

    @app.route("/api/db/scenes/<scene_id>/messages", methods=["POST"])
    def db_append_message(scene_id):
        conn = _conn(db_path)
        if conn.execute("SELECT 1 FROM scenes WHERE id = ?", (scene_id,)).fetchone() is None:
            conn.close()
            return jsonify({"error": "not_found"}), 404
        body = request.get_json(force=True) or {}
        author_name = body.get("author_name", "").strip()
        content_original = body.get("content_original")
        if not author_name or content_original is None:
            conn.close()
            return jsonify({"error": "bad_request"}), 400
        mid = db_messages.add_message(conn, scene_id=scene_id,
            author_name=author_name, content_original=content_original,
            character_id=body.get("character_id"),
            content_enhanced=body.get("content_enhanced"),
            source=body.get("source", "manual"),
            is_summary=body.get("is_summary", 0))
        conn.close()
        return jsonify({"id": mid}), 201

    @app.route("/api/db/scenes/<scene_id>/messages", methods=["GET"])
    def get_scene_messages_paginated(scene_id):
        conn = _conn(db_path)
        # 404 se scena non esiste
        scene_row = conn.execute("SELECT id FROM scenes WHERE id=?", (scene_id,)).fetchone()
        if not scene_row:
            conn.close()
            return jsonify({"error": "not found"}), 404
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 50))
        # page è 1-based, per_page deve essere positivo (evita div-by-zero nel calcolo pages)
        if page < 1 or per_page < 1:
            conn.close()
            return jsonify({"error": "bad_request"}), 400
        result = db_messages.get_scene_message_page(conn, scene_id, page, per_page)
        conn.close()
        return jsonify(result), 200

    @app.route("/api/db/scenes/<scene_id>/messages/count", methods=["GET"])
    def db_count_messages(scene_id):
        conn = _conn(db_path)
        # Verifica esistenza scena per distinguere 404 da count 0
        if conn.execute("SELECT 1 FROM scenes WHERE id = ?", (scene_id,)).fetchone() is None:
            conn.close()
            return jsonify({"error": "not_found"}), 404
        count = db_messages.count_messages_for_scene(conn, scene_id)
        conn.close()
        return jsonify({"count": count, "scene_id": scene_id}), 200

    @app.route("/api/db/scenes/<scene_id>/messages/insert", methods=["POST"])
    def db_insert_message_at(scene_id):
        conn = _conn(db_path)
        if conn.execute("SELECT 1 FROM scenes WHERE id = ?", (scene_id,)).fetchone() is None:
            conn.close()
            return jsonify({"error": "not_found"}), 404

        body = request.get_json(force=True) or {}
        required_fields = ["author_name", "content_original", "position_order"]
        if not all(k in body for k in required_fields):
            conn.close()
            return jsonify({"error": "bad_request"}), 400

        mid = db_messages.insert_message_at(
            conn,
            scene_id=scene_id,
            author_name=body["author_name"],
            content_original=body["content_original"],
            position_order=body["position_order"],
        )
        conn.close()
        return jsonify({"id": mid}), 201

    @app.route("/api/db/scenes/<scene_id>/messages/compact", methods=["POST"])
    def db_compact_scene_messages(scene_id):
        conn = _conn(db_path)
        if conn.execute("SELECT 1 FROM scenes WHERE id = ?", (scene_id,)).fetchone() is None:
            conn.close()
            return jsonify({"error": "not_found"}), 404
        count = db_messages.compact_scene_positions(conn, scene_id)
        conn.close()
        return jsonify({"count": count}), 200
