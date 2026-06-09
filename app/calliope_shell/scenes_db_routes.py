"""
REST endpoints scene-as-chat su DB SQLite (app.db).

GAP WIRING (CALLIOPE_GAP_NIGHT_2026-06-08, WI-3/WI-4/WI-5/WI-9):
`server.py:create_app()` NON importava mai `app.db` → la dashboard serviva ancora
il vecchio modello scene flat-YAML. Questo modulo cabla il layer DB GIA' testato
(`app/db/messages.py`, `app/db/reactions.py`, migration 001/002) dentro Flask.

Route (tutte sotto /api/db):
  GET  /api/db/scenes                            -> lista scene            (WI-3)
  GET  /api/db/scenes/<scene_id>                 -> dettaglio + messaggi    (WI-3)
  POST /api/db/scenes/<scene_id>/messages        -> append messaggio        (WI-4)
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

from flask import jsonify, request  # noqa: F401  # request usato dai corpi route WI-4/WI-5

from app.db import get_db
from app.db import messages as db_messages  # noqa: F401  # usato dai corpi route WI-3/WI-4
from app.db import reactions as db_reactions  # noqa: F401  # usato dai corpi route WI-5


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
        # TODO(WI-4): conn = _conn(db_path)
        #   if conn.execute("SELECT 1 FROM scenes WHERE id = ?", (scene_id,)).fetchone() is None:
        #       conn.close(); return jsonify({"error": "not_found"}), 404
        #   body = request.get_json(force=True) or {}
        #   mid = db_messages.add_message(conn, scene_id=scene_id,
        #       author_name=body["author_name"], content_original=body["content_original"],
        #       character_id=body.get("character_id"))
        #   conn.close(); return jsonify({"id": mid}), 201
        return jsonify({"error": "not_implemented", "wi": "WI-4"}), 501

    @app.route("/api/db/messages/<message_id>/reactions", methods=["GET"])
    def db_list_reactions(message_id):
        # TODO(WI-5): conn = _conn(db_path)
        #   data = db_reactions.list_reactions(conn, message_id=message_id)
        #   conn.close(); return jsonify({"reactions": list(data)}), 200
        return jsonify({"error": "not_implemented", "wi": "WI-5"}), 501

    @app.route("/api/db/messages/<message_id>/reactions", methods=["POST"])
    def db_add_reaction(message_id):
        # TODO(WI-5): conn = _conn(db_path)
        #   body = request.get_json(force=True) or {}
        #   rid = db_reactions.add_reaction(conn, message_id=message_id,
        #       character_id=body["character_id"], emoji=body.get("emoji", ""))
        #   conn.close(); return jsonify({"id": rid}), 201
        return jsonify({"error": "not_implemented", "wi": "WI-5"}), 501

    return app
