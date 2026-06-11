"""
Route DB-backed per i personaggi-in-scena (/api/db/scenes/<id>/characters).

Estratto da scenes_db_routes.py (refactor 2026-06-11, slice 3: split del monolite
per ridurre il contesto-edit e sbloccare i modelli cost-zero su questa risorsa).
Registrato transitivamente da register_scenes_db_routes (backward-compat).
"""

from __future__ import annotations

import sqlite3

from flask import jsonify, request

from app.db import get_db
from app.db import characters as db_characters


def _conn(db_path):
    """Apre una connessione: db_path esplicito (test temp) o default produzione."""
    return get_db(db_path) if db_path else get_db()


def register_scene_characters_db_routes(app, db_path=None):
    """Registra gli endpoint personaggi-in-scena sul Flask ``app``."""

    @app.route("/api/db/scenes/<scene_id>/characters", methods=["GET"])
    def list_scene_characters(scene_id):
        conn = _conn(db_path)
        # 404 se la scena non esiste (WI-57): allinea con GET /scenes/<id> e /messages
        if conn.execute("SELECT 1 FROM scenes WHERE id=?", (scene_id,)).fetchone() is None:
            conn.close()
            return jsonify({"error": "not_found"}), 404
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
        # campo obbligatorio mancante → 400, non 404 (WI-59 FIX A)
        if not char_id:
            conn.close()
            return jsonify({"error": "character_id required"}), 400
        char_row = conn.execute(
            "SELECT id FROM characters WHERE id=?", (char_id,)
        ).fetchone()
        if not char_row:
            conn.close()
            return jsonify({"error": "not found"}), 404
        # role vuoto/assente → fallback al DEFAULT logico 'participant' (WI-59 FIX B)
        role = data.get("role") or "participant"
        try:
            db_characters.add_character_to_scene(conn, scene_id, char_id, role)
        except sqlite3.IntegrityError:
            # UNIQUE (scene_id, character_id) già presente → conflitto (WI-28)
            conn.close()
            return jsonify({"error": "conflict"}), 409
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
