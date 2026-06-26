"""REST endpoints scene-as-chat su DB SQLite (app.db).

Route (tutte sotto /api/db):
  GET  /api/db/scenes                            -> lista scene
  GET  /api/db/scenes/<scene_id>                 -> dettaglio + messaggi
  POST /api/db/scenes/<scene_id>/messages        -> append messaggio
  GET  /api/db/scenes/<scene_id>/messages        -> paginazione messaggi
  GET  /api/db/messages/<message_id>/reactions   -> lista reazioni
  POST /api/db/messages/<message_id>/reactions   -> aggiungi reazione
"""
from __future__ import annotations

from flask import jsonify, request

from app.db import get_db, new_id
from app.db import messages as db_messages
from app.db import scenes as db_scenes
from app.calliope_shell.reactions_db_routes import register_reactions_db_routes
from app.calliope_shell.messages_db_routes import register_messages_db_routes
from app.calliope_shell.scene_characters_db_routes import (
    register_scene_characters_db_routes,
)


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
    # Refactor 2026-06-11: le route reazioni vivono in reactions_db_routes.py
    # (modulo piccolo, cost-zero-friendly). Le registriamo qui per backward-compat
    # con i test/chiamanti che usano SOLO register_scenes_db_routes come entrypoint.
    register_reactions_db_routes(app, db_path=db_path)
    register_messages_db_routes(app, db_path=db_path)
    register_scene_characters_db_routes(app, db_path=db_path)

    @app.route("/api/db/scenes", methods=["GET"])
    def db_list_scenes():
        # WI-44: filtro opzionale ?arc_id=<id> (assente → tutte le scene).
        # WI-35: filtro opzionale ?title=<substr> (LIKE case-insensitive).
        conn = _conn(db_path)
        title = request.args.get("title")
        if title is not None:
            scenes = db_scenes.list_scenes(conn, title_contains=title)
            conn.close()
            return jsonify({"scenes": scenes}), 200
        arc_id = request.args.get("arc_id")
        select = (
            "SELECT s.id, s.title, s.arc_id, s.location, s.is_readonly, "
            "s.last_activity_at, s.updated_at, COUNT(m.id) AS message_count "
            "FROM scenes s LEFT JOIN messages m ON m.scene_id = s.id"
        )
        group = " GROUP BY s.id"
        order = " ORDER BY COALESCE(s.last_activity_at, s.updated_at) DESC"
        if arc_id is not None:
            cur = conn.execute(select + " WHERE s.arc_id = ?" + group + order, (arc_id,))
        else:
            cur = conn.execute(select + group + order)
        scenes = [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]
        conn.close()
        return jsonify({"scenes": scenes}), 200

    @app.route("/api/db/scenes/<scene_id>/arc", methods=["PATCH"])
    def db_assign_scene_arc(scene_id):
        # WI-38: assegna/disassocia l'arco (arc_id può essere null).
        body = request.get_json(silent=True) or {}
        if "arc_id" not in body:
            return jsonify({"error": "bad_request"}), 400
        conn = _conn(db_path)
        ok = db_scenes.assign_scene_to_arc(conn, scene_id, body.get("arc_id"))
        conn.close()
        if not ok:
            return jsonify({"error": "not_found"}), 404
        return jsonify({}), 200

    @app.route("/api/db/scenes/<scene_id>", methods=["DELETE"])
    def db_delete_scene(scene_id):
        # WI-33: schema ha ON DELETE CASCADE su messages/scene_characters.
        conn = _conn(db_path)
        cur = conn.execute("DELETE FROM scenes WHERE id = ?", (scene_id,))
        conn.commit()
        conn.close()
        if cur.rowcount > 0:
            return "", 204
        return jsonify({"error": "not_found"}), 404


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

    @app.route("/api/db/scenes", methods=["POST"])
    def db_create_scene():
        # WI-64: crea scena con campo opzionale location.
        body = request.get_json(silent=True) or {}
        title = body.get("title")
        if not title:
            return jsonify({"error": "title required"}), 400
        title = title.strip()
        if not title:
            return jsonify({"error": "title required"}), 400
        location = body.get("location")
        scene_id = new_id()
        conn = _conn(db_path)
        conn.execute(
            "INSERT INTO scenes (id, title, location) VALUES (?, ?, ?)",
            (scene_id, title, location),
        )
        conn.commit()
        conn.close()
        return jsonify({"id": scene_id, "title": title, "location": location}), 201

    @app.route("/api/db/scenes/<scene_id>", methods=["PATCH"])
    def db_update_scene(scene_id):
        # WI-65: aggiorna title e/o location (solo i campi forniti).
        body = request.get_json(silent=True) or {}
        if "title" not in body and "location" not in body:
            return jsonify({"error": "no updatable fields"}), 400
        if "title" in body and not body.get("title"):
            return jsonify({"error": "title cannot be empty"}), 400
        conn = _conn(db_path)
        row = conn.execute(
            "SELECT id FROM scenes WHERE id = ?", (scene_id,)
        ).fetchone()
        if row is None:
            conn.close()
            return jsonify({"error": "not_found"}), 404
        sets, params = ["updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now')"], []
        if "title" in body:
            sets.append("title = ?")
            params.append(body.get("title"))
        if "location" in body:
            sets.append("location = ?")
            params.append(body.get("location"))
        params.append(scene_id)
        conn.execute(f"UPDATE scenes SET {', '.join(sets)} WHERE id = ?", params)
        conn.commit()
        conn.close()
        return jsonify({}), 200

    @app.route("/api/db/scenes/merge", methods=["POST"])
    def db_merge_scenes():
        conn = _conn(db_path)
        body = request.get_json(force=True) or {}
        required = ["scene_id_a", "scene_id_b", "new_name"]
        if not all(k in body for k in required):
            conn.close()
            return jsonify({"error": "bad_request"}), 400

        scene_id_a = body["scene_id_a"]
        scene_id_b = body["scene_id_b"]
        new_name = body["new_name"]

        # Guard self-merge (WI-52): a==b → bad_request (distinto dal not_found)
        if scene_id_a == scene_id_b:
            conn.close()
            return jsonify({"error": "bad_request"}), 400

        # Guard: verifica esistenza scene_id_a
        if conn.execute("SELECT 1 FROM scenes WHERE id = ?", (scene_id_a,)).fetchone() is None:
            conn.close()
            return jsonify({"error": "not_found"}), 404

        # Guard: verifica esistenza scene_id_b
        if conn.execute("SELECT 1 FROM scenes WHERE id = ?", (scene_id_b,)).fetchone() is None:
            conn.close()
            return jsonify({"error": "not_found"}), 404

        try:
            merged_scene_id = db_messages.merge_scenes(
                conn,
                scene_id_a,
                scene_id_b,
                new_name,
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

    return app
