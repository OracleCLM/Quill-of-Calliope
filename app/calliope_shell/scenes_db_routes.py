"""
REST endpoints scene-as-chat su DB SQLite (app.db).

GAP WIRING (CALLIOPE_GAP_NIGHT_2026-06-08, WI-3/WI-4/WI-5/WI-9):
`server.py:create_app()` NON importava mai `app.db` -> la dashboard serviva ancora
il vecchio modello scene flat-YAML. Questo modulo cabla il layer DB GIA' testato
(`app/db/messages.py`, `app/db/reactions.py`, migration 001/002) dentro Flask.

Route (tutte sotto /api/db):
  GET  /api/db/scenes                            -> lista scene            (WI-3)
  GET  /api/db/scenes/<scene_id>                 -> dettaglio + messaggi    (WI-3)
  POST /api/db/scenes/<scene_id>/messages        -> append messaggio        (WI-4)
  GET  /api/db/scenes/<scene_id>/messages        -> paginazione messaggi    (WI-12)
  GET  /api/db/messages/<message_id>/reactions   -> lista reazioni          (WI-5)
  POST /api/db/messages/<message_id>/reactions   -> aggiungi reazione       (WI-5)

SPLIT DI RUOLO (operator-mandate orch-efesto):
  - FORNITO dal father (questo file): la WIRING mancante = funzione
    `register_scenes_db_routes(app, db_path=None)` + registrazione route +
    firme. Questo era il gap critico.
  - DA COMPLETARE dal worker Efesto: i CORPI delle route (marcati `TODO(WI-n)`),
    usando ESCLUSIVAMENTE l'API gia' testata di `app.db`. NON inventare schema,
    NON creare nuove migration: le tabelle scenes/messages/scene_reactions
    esistono gia'.

ACCETTAZIONE: `pytest tests/unit/test_scenes_db_routes.py -q` deve passare.
NON modificare le assertion del test: e' il contratto.
"""
from __future__ import annotations

from flask import jsonify, request

from app.db import get_db
from app.db import characters as db_characters
from app.db import messages as db_messages
from app.db import reactions as db_reactions


def _conn(db_path):
    """Apre una connessione: db_path esplicito (test temp) o default produzione."""
    return get_db(db_path) if db_path else get_db()


def register_scenes_db_routes(app, db_path=None):
    """Registra gli endpoint scene-as-chat DB-backed sul Flask `app`.

    Parameters
    ----------
    app : Flask
        L'app a cui agganciare le route (chiamata da `create_app()`).
    db_path : str | Path | None
        Override opzionale del path DB (i test iniettano un DB temporaneo).
        None -> default produzione (`app.db.CALLIOPE_DB_PATH`).
    """

    @app.route("/api/db/scenes", methods=["GET"])
    def db_list_scenes():
        conn = _conn(db_path)
        cur = conn.execute(
            "SELECT id, title, arc_id, location, last_activity_at, updated_at "
            "FROM scenes ORDER BY COALESCE(last_activity_at, updated_at) DESC"
        )
        scenes = [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]
        conn.close()
        return jsonify({"scenes": scenes}), 200

    @app.route("/api/db/scenes/<scene_id>", methods=["GET"])
    def db_scene_detail(scene_id):
        conn = _conn(db_path)
        row = conn.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,)).fetchone()
        if row is None:
            conn.close()
            return jsonify({"error": "not_found"}), 404
        scene = dict(row)
        msgs = db_messages.list_messages_for_scene(conn, scene_id)
        conn.close()
        return jsonify({"scene": scene, "messages": list(msgs)}), 200

    @app.route("/api/db/scenes/<scene_id>/messages", methods=["POST"])
    def db_append_message(scene_id):
        conn = _conn(db_path)
        if conn.execute("SELECT 1 FROM scenes WHERE id = ?", (scene_id,)).fetchone() is None:
            conn.close()
            return jsonify({"error": "not_found"}), 404
        body = request.get_json(force=True) or {}
        mid = db_messages.add_message(conn, scene_id=scene_id,
            author_name=body["author_name"], content_original=body["content_original"],
            character_id=body.get("character_id"))
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
        result = db_messages.get_scene_message_page(conn, scene_id, page, per_page)
        conn.close()
        return jsonify(result), 200

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
        rid = db_reactions.add_reaction(conn, message_id=message_id,
            character_id=body["character_id"], emoji=body.get("emoji", ""))
        conn.close()
        return jsonify({"id": rid}), 201

    @app.route("/api/db/scenes/<scene_id>/characters", methods=["GET"])
    def list_scene_characters(scene_id):
        conn = _conn(db_path)
        chars = db_characters.list_characters_in_scene(conn, scene_id)
        conn.close()
        return jsonify({"characters": [dict(c) for c in chars]}), 200

    @app.route("/api/db/scenes/<scene_id>/characters", methods=["POST"])
    def add_character_to_scene_route(scene_id):
        conn = _conn(db_path)
        scene_row = conn.execute(
            "SELECT id FROM scenes WHERE id=?", (scene_id,)
        ).fetchone()
        if not scene_row:
            conn.close()
            return jsonify({"error": "not found"}), 404
        data = request.get_json(silent=True) or {}
        char_id = data.get("character_id")
        char_row = conn.execute(
            "SELECT id FROM characters WHERE id=?", (char_id,)
        ).fetchone()
        if not char_row:
            conn.close()
            return jsonify({"error": "not found"}), 404
        role = data.get("role", "")
        db_characters.add_character_to_scene(conn, scene_id, char_id, role)
        conn.close()
        return jsonify({}), 201

    @app.route("/api/db/scenes/<scene_id>/characters/<character_id>", methods=["DELETE"])
    def db_remove_character_from_scene(scene_id, character_id):
        conn = _conn(db_path)
        if db_characters.remove_character_from_scene(conn, scene_id, character_id):
            conn.close()
            return jsonify({}), 204
        conn.close()
        return jsonify({"error": "not_found"}), 404

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

    @app.route("/api/db/scenes/merge", methods=["POST"])
    def db_merge_scenes():
        conn = _conn(db_path)
        body = request.get_json(force=True) or {}
        required = ["scene_id_a", "scene_id_b", "new_name"]
        if not all(k in body for k in required):
            conn.close()
            return jsonify({"error": "bad_request"}), 400
        try:
            merged_scene_id = db_messages.merge_scenes(
                conn,
                body["scene_id_a"],
                body["scene_id_b"],
                body["new_name"],
            )
            conn.close()
            return jsonify({"merged_scene_id": merged_scene_id}), 201
        except ValueError:
            conn.close()
            return jsonify({"error": "not_found"}), 404

    @app.route("/api/db/scenes/<scene_id>/duplicate", methods=["POST"])
    def db_duplicate_scene(scene_id):
        conn = _conn(db_path)
        body = request.get_json(force=True) or {}
        new_name = body.get("new_name")

        if not new_name:
            conn.close()
            return jsonify({"error": "bad_request"}), 400

        # Verifica esplicita dell'esistenza della scena (Guard)
        if conn.execute("SELECT 1 FROM scenes WHERE id = ?", (scene_id,)).fetchone() is None:
            conn.close()
            return jsonify({"error": "not_found"}), 404

        new_scene_id = db_messages.duplicate_scene(
            conn, scene_id, new_name
        )
        conn.close()
        return jsonify({"new_scene_id": new_scene_id}), 201

    @app.route("/api/db/scenes/<scene_id>/messages/compact", methods=["POST"])
    def db_compact_scene_messages(scene_id):
        conn = _conn(db_path)
        if conn.execute("SELECT 1 FROM scenes WHERE id = ?", (scene_id,)).fetchone() is None:
            conn.close()
            return jsonify({"error": "not_found"}), 404
        count = db_messages.compact_scene_positions(conn, scene_id)
        conn.close()
        return jsonify({"count": count}), 200

    return app
