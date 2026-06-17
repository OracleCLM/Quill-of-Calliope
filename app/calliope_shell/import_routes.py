"""GAP-4: importer storico Discord IN-UI (espone lo scraping/parse CLI esistente).

VISION scene-chat: i messaggi degli altri personaggi sono importati da Discord (scraping
per-canale/data, **selezione manuale**). Il parser ``parse_channel`` (scripts/import_discord_history.py)
processa gli export DiscordChatExporter; qui lo esponiamo via HTTP per un flusso in-UI:
scan cartella -> anteprima per-canale -> selezione manuale -> import nella scena scelta.
"""

from __future__ import annotations

import json
from pathlib import Path

from flask import jsonify, request

from app.db import get_db
from app.db import messages as db_messages


def _conn(db_path):
    return get_db(db_path) if db_path else get_db()


def _load_parser():
    """Importa parse_channel dallo script CLI (riuso, niente duplicazione)."""
    import importlib.util  # noqa: PLC0415

    script = Path(__file__).parents[2] / "scripts" / "import_discord_history.py"
    spec = importlib.util.spec_from_file_location("import_discord_history", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.parse_channel


def register_import_routes(app, db_path=None):
    """Registra gli endpoint dell'importer Discord in-UI."""

    @app.route("/api/import/discord/scan", methods=["POST"])
    def import_scan():
        body = request.get_json(silent=True) or {}
        d = (body.get("dir") or "").strip()
        if not d:
            return jsonify({"error": "dir required"}), 400
        path = Path(d).expanduser()
        if not path.is_dir():
            return jsonify({"error": "directory non trovata", "dir": str(path)}), 404
        files = []
        for f in sorted(path.glob("*.json")):
            count = None
            try:
                with f.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                count = len(data.get("messages", []))
                channel = (data.get("channel") or {}).get("name", "")
            except Exception:
                channel = ""
            files.append({"file": f.name, "channel": channel, "count": count})
        return jsonify({"dir": str(path), "files": files}), 200

    @app.route("/api/import/discord/preview", methods=["POST"])
    def import_preview():
        body = request.get_json(silent=True) or {}
        d = (body.get("dir") or "").strip()
        fname = (body.get("file") or "").strip()
        if not d or not fname:
            return jsonify({"error": "dir e file richiesti"}), 400
        path = (Path(d).expanduser() / fname).resolve()
        # Sicurezza: il file deve stare DENTRO la dir indicata.
        base = Path(d).expanduser().resolve()
        if base not in path.parents or path.suffix != ".json":
            return jsonify({"error": "percorso non valido"}), 400
        if not path.is_file():
            return jsonify({"error": "file non trovato"}), 404
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            records = _load_parser()(data, set())
        except Exception as exc:
            return jsonify({"error": f"parse fallito: {exc}"}), 422
        msgs = [
            {
                "message_id": r.get("message_id"),
                "timestamp": r.get("timestamp"),
                "author_name": r.get("author_name"),
                "content": r.get("content"),
                "tag": r.get("tag"),
            }
            for r in records[:1000]
        ]
        channel = (data.get("channel") or {}).get("name", "")
        return jsonify({"channel": channel, "count": len(records), "messages": msgs}), 200

    @app.route("/api/import/discord/to-scene", methods=["POST"])
    def import_to_scene():
        body = request.get_json(silent=True) or {}
        scene_id = body.get("scene_id")
        messages = body.get("messages") or []
        if not scene_id or not isinstance(messages, list) or not messages:
            return jsonify({"error": "scene_id e messages[] richiesti"}), 400
        conn = _conn(db_path)
        if conn.execute("SELECT 1 FROM scenes WHERE id=?", (scene_id,)).fetchone() is None:
            conn.close()
            return jsonify({"error": "not_found"}), 404
        row = conn.execute(
            "SELECT COALESCE(MAX(position_order), -1) + 1 FROM messages WHERE scene_id=?",
            (scene_id,),
        ).fetchone()
        pos = row[0]
        imported = 0
        for m in messages:
            author = (m.get("author_name") or "").strip()
            content = m.get("content")
            if not author or content is None:
                continue
            db_messages.add_message(
                conn, scene_id=scene_id, author_name=author,
                content_original=content, source="discord_import", position_order=pos,
            )
            pos += 1
            imported += 1
        conn.execute(
            "UPDATE scenes SET last_activity_at = strftime('%Y-%m-%d %H:%M:%f','now') WHERE id=?",
            (scene_id,),
        )
        conn.commit()
        conn.close()
        return jsonify({"imported": imported}), 201
