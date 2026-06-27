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

    @app.route("/api/db/messages/recent", methods=["GET"])
    def db_messages_recent():
        # Recent-messages cross-scena per il pannello nav-messages
        # (post-import, WI-NAVMSG-1).
        # Route statica → precede /api/db/messages/<message_id> nel routing Flask.
        limit = request.args.get("limit", default=50, type=int)
        if limit <= 0:
            return jsonify({"error": "bad_request"}), 400
        char = request.args.get("char")
        source = request.args.get("source")
        conn = _conn(db_path)
        sql = "SELECT id, scene_id, author_name, content_original, ts, source FROM messages"
        where: list[str] = []
        params: list = []
        if char:
            where.append("author_name LIKE ? COLLATE NOCASE")
            params.append(f"%{char}%")
        if source:
            where.append("source = ?")
            params.append(source)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        cols = ("id", "scene_id", "author_name", "content_original", "ts", "source")
        messages = [dict(zip(cols, tuple(r))) for r in rows]
        return jsonify({"messages": messages, "count": len(messages)}), 200

    @app.route("/api/db/messages/<message_id>/position", methods=["PATCH"])
    def db_update_message_position(message_id):
        conn = _conn(db_path)
        body = request.get_json(force=True) or {}

        if "position" not in body:
            conn.close()
            return jsonify({"error": "bad_request"}), 400

        position = body["position"]
        if not isinstance(position, int) or position < 0:
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
        content_enhanced = body.get("content_enhanced")
        if content_original is None and author_name is None and content_enhanced is None:
            return jsonify({"error": "bad_request"}), 400
        conn = _conn(db_path)
        updated = db_messages.update_message(
            conn, message_id,
            content_original=content_original,
            author_name=author_name,
            content_enhanced=content_enhanced,
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
        scene_row = conn.execute("SELECT is_readonly FROM scenes WHERE id = ?", (scene_id,)).fetchone()
        if scene_row is None:
            conn.close()
            return jsonify({"error": "not_found"}), 404
        if scene_row[0]:
            conn.close()
            return jsonify({"error": "readonly"}), 403
        body = request.get_json(force=True) or {}
        author_name = body.get("author_name", "").strip()
        content_original = body.get("content_original")
        if not author_name or content_original is None:
            conn.close()
            return jsonify({"error": "bad_request"}), 400
        # BUG-FIX (message-render): usare MAX(position_order)+1, NON len(messages).
        # Le scene importate da Discord hanno position_order non-contigui (es. 66..16541);
        # con len() il nuovo turno riceveva una position bassa e si ordinava a META'/IN-CIMA
        # al thread invece che in fondo -> "il messaggio non appare nella scena" (era persistito
        # ma sepolto in alto). MAX+1 garantisce l'append in coda con qualunque distribuzione.
        row = conn.execute(
            "SELECT COALESCE(MAX(position_order), -1) + 1 FROM messages WHERE scene_id = ?",
            (scene_id,),
        ).fetchone()
        position_order = row[0]
        mid = db_messages.add_message(conn, scene_id=scene_id,
            author_name=author_name, content_original=content_original,
            character_id=body.get("character_id"),
            content_enhanced=body.get("content_enhanced"),
            source=body.get("source", "manual"),
            is_summary=body.get("is_summary", 0),
            position_order=position_order)
        # traccia ultima attività scena per sorting recente nel dashboard (WI-48).
        # Precisione al ms (strftime %f) per ordinamento deterministico fra append ravvicinati.
        conn.execute(
            "UPDATE scenes SET last_activity_at = strftime('%Y-%m-%d %H:%M:%f', 'now') WHERE id = ?",
            (scene_id,),
        )
        conn.commit()
        conn.close()
        return jsonify({"id": mid}), 201

    @app.route("/api/db/scenes/<scene_id>/messages/<message_id>/refine", methods=["POST"])
    def db_refine_message(scene_id, message_id):
        # Wiring refine end-to-end: invoca la refine-fn E3 (gateway-strong +
        # retrieval schede-attive+lore via build_refine_prompt) e ritorna
        # content_original + content_enhanced (E3 popola gia content_enhanced nel DB).
        conn = _conn(db_path)
        if conn.execute("SELECT 1 FROM scenes WHERE id = ?", (scene_id,)).fetchone() is None:
            conn.close()
            return jsonify({"error": "not_found"}), 404
        row = conn.execute(
            "SELECT content_original FROM messages WHERE id = ? AND scene_id = ?",
            (message_id, scene_id),
        ).fetchone()
        if row is None:
            conn.close()
            return jsonify({"error": "not_found"}), 404
        from app.calliope_shell.lore_kb import LoreStore
        from app.calliope_shell.scene_refine import WriteModelError, refine_message
        content_original = row[0]
        try:
            enhanced = refine_message(message_id, scene_id, conn, LoreStore())
        except WriteModelError as exc:
            # Resilienza-503: messaggio-utente pulito, NON errore grezzo, NON clobber.
            conn.close()
            if exc.kind == "bad_request":
                return jsonify({
                    "error": "bad_request",
                    "message": "Il testo del messaggio non è valido per il raffinamento.",
                }), 400
            if exc.kind == "auth":
                return jsonify({
                    "error": "gateway_auth",
                    "message": "Configurazione del modello di scrittura non valida (credenziali). Controlla il gateway.",
                }), 502
            return jsonify({
                "error": "gateway_overloaded",
                "message": "Il modello di scrittura è momentaneamente sovraccarico. Riprova tra qualche secondo.",
            }), 503
        conn.close()
        return jsonify({
            "message_id": message_id,
            "content_original": content_original,
            "content_enhanced": enhanced,
        }), 200

    @app.route("/api/db/scenes/<scene_id>/messages", methods=["GET"])
    def get_scene_messages_paginated(scene_id):
        conn = _conn(db_path)
        # 404 se scena non esiste
        scene_row = conn.execute("SELECT id FROM scenes WHERE id=?", (scene_id,)).fetchone()
        if not scene_row:
            conn.close()
            return jsonify({"error": "not found"}), 404
        try:
            page = int(request.args.get("page", 1))
            per_page = int(request.args.get("per_page", 50))
        except (ValueError, TypeError):
            conn.close()
            return jsonify({"error": "bad_request"}), 400
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
        # position_order deve essere un intero non-negativo (WI-58)
        pos = body.get("position_order")
        if not isinstance(pos, int) or pos < 0:
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
