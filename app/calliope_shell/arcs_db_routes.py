"""
Route DB-backed per gli archi narrativi (arcs).

Espone gli endpoint CRUD ``/api/db/arcs`` + l'associazione scene→arco.
Registrato da ``server.py:create_app()`` via ``register_arcs_db_routes``.
"""

from __future__ import annotations

from flask import jsonify, request

from app.db import get_db
from app.db import arcs as db_arcs


def _conn(db_path):
    """Apre una connessione: db_path esplicito (test temp) o default produzione."""
    return get_db(db_path) if db_path else get_db()


def register_arcs_db_routes(app, *, db_path=None):
    """Registra gli endpoint arc DB-backed sul Flask ``app``.

    db_path (keyword-only): override opzionale del path DB (i test iniettano
    un DB temporaneo); None → default produzione.
    """

    @app.route("/api/db/arcs", methods=["POST"])
    def db_create_arc():
        body = request.get_json(silent=True) or {}
        title = body.get("title")
        if not title:
            return jsonify({"error": "title required"}), 400
        description = body.get("description", "")
        conn = _conn(db_path)
        arc_id = db_arcs.create_arc(conn, title, description)
        conn.close()
        return jsonify({"id": arc_id, "title": title}), 201

    @app.route("/api/db/arcs", methods=["GET"])
    def db_list_arcs():
        conn = _conn(db_path)
        arcs = db_arcs.list_arcs(conn)
        conn.close()
        return jsonify({"arcs": arcs}), 200

    @app.route("/api/db/arcs/<arc_id>", methods=["GET"])
    def db_get_arc(arc_id):
        conn = _conn(db_path)
        arc = db_arcs.get_arc(conn, arc_id)
        conn.close()
        if arc is None:
            return jsonify({"error": "not_found"}), 404
        return jsonify(arc), 200

    @app.route("/api/db/arcs/<arc_id>", methods=["DELETE"])
    def db_delete_arc(arc_id):
        conn = _conn(db_path)
        deleted = db_arcs.delete_arc(conn, arc_id)
        conn.close()
        if not deleted:
            return jsonify({"error": "not_found"}), 404
        return "", 204

    @app.route("/api/db/arcs/<arc_id>/scenes", methods=["GET"])
    def db_arc_scenes(arc_id):
        conn = _conn(db_path)
        arc = db_arcs.get_arc(conn, arc_id)
        if arc is None:
            conn.close()
            return jsonify({"error": "not_found"}), 404
        scenes = db_arcs.list_scenes_for_arc(conn, arc_id)
        conn.close()
        return jsonify({"scenes": scenes, "arc_id": arc_id}), 200
