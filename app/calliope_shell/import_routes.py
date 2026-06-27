"""GAP-4: importer storico Discord IN-UI (espone lo scraping/parse CLI esistente).

VISION scene-chat: i messaggi degli altri personaggi sono importati da Discord (scraping
per-canale/data, **selezione manuale**). Il parser ``parse_channel`` (scripts/import_discord_history.py)
processa gli export DiscordChatExporter; qui lo esponiamo via HTTP per un flusso in-UI:
scan cartella -> anteprima per-canale -> selezione manuale -> import nella scena scelta.
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from flask import jsonify, request

from app.calliope_shell import discord_live
from app.db import get_db
from app.db import messages as db_messages


def _conn(db_path):
    return get_db(db_path) if db_path else get_db()


def _filter_by_span(records, since, until):
    """Filter parsed records by ISO ``timestamp`` within [since, until].

    ``since``/``until`` are ISO date/datetime strings (or None = no bound).
    Comparison is lexicographic on the ISO timestamp prefix, which is correct for
    UTC ISO-8601 strings. Records without a timestamp are kept (no basis to drop).
    """
    if not since and not until:
        return records
    out = []
    for r in records:
        ts = (r.get("timestamp") or "").strip()
        if not ts:
            out.append(r)
            continue
        if since and ts < since:
            continue
        if until and ts > until:
            continue
        out.append(r)
    return out


def _channel_meta(data):
    """Extract channel metadata (name, parent_category, count, date-range)."""
    channel = data.get("channel") or {}
    msgs = data.get("messages") or []
    timestamps = [m.get("timestamp") for m in msgs if m.get("timestamp")]
    first = min(timestamps) if timestamps else None
    last = max(timestamps) if timestamps else None
    return {
        "channel": channel.get("name", ""),
        "channel_id": str(channel.get("id", "")) or None,
        "parent_category": channel.get("category") or channel.get("categoryName") or None,
        "count": len(msgs),
        "date_from": first,
        "date_to": last,
    }


def _safe_resolve(base_dir, fname):
    """Resolve ``fname`` inside ``base_dir``; return Path or None if escaping/invalid."""
    base = Path(base_dir).expanduser().resolve()
    path = (base / fname).resolve()
    if (base not in path.parents and path.parent != base) or path.suffix != ".json":
        return None
    return path


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
            entry = {
                "file": f.name, "channel": "", "count": None,
                "channel_id": None, "parent_category": None,
                "date_from": None, "date_to": None,
            }
            try:
                with f.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                entry.update(_channel_meta(data))
            except Exception:
                pass
            files.append(entry)
        return jsonify({"dir": str(path), "files": files}), 200

    @app.route("/api/import/discord/preview", methods=["POST"])
    def import_preview():
        body = request.get_json(silent=True) or {}
        d = (body.get("dir") or "").strip()
        # Multi-canale: accetta `files` (lista) o `file` (singolo, back-compat).
        fnames = body.get("files")
        if not isinstance(fnames, list):
            fnames = []
        single = (body.get("file") or "").strip()
        if single:
            fnames = [single] + [f for f in fnames if f != single]
        fnames = [str(f).strip() for f in fnames if str(f).strip()]
        if not d or not fnames:
            return jsonify({"error": "dir e file/files richiesti"}), 400
        since = (body.get("since") or "").strip() or None
        until = (body.get("until") or "").strip() or None

        parser = _load_parser()
        all_records = []
        channels = []
        for fname in fnames:
            path = _safe_resolve(d, fname)
            if path is None:
                return jsonify({"error": f"percorso non valido: {fname}"}), 400
            if not path.is_file():
                return jsonify({"error": f"file non trovato: {fname}"}), 404
            try:
                with path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                records = parser(data, set())
            except Exception as exc:
                return jsonify({"error": f"parse fallito ({fname}): {exc}"}), 422
            records = _filter_by_span(records, since, until)
            all_records.extend(records)
            channels.append((data.get("channel") or {}).get("name", ""))

        msgs = [
            {
                "message_id": r.get("message_id"),
                "timestamp": r.get("timestamp"),
                "author_name": r.get("author_name"),
                "content": r.get("content"),
                "tag": r.get("tag"),
                "channel_name": r.get("channel_name"),
            }
            for r in all_records[:1000]
        ]
        # Back-compat: `channel` resta il primo canale; `channels` la lista completa.
        return jsonify({
            "channel": channels[0] if channels else "",
            "channels": channels,
            "count": len(all_records),
            "messages": msgs,
        }), 200

    @app.route("/api/import/discord/to-scene", methods=["POST"])
    def import_to_scene():
        body = request.get_json(silent=True) or {}
        scene_id = body.get("scene_id")
        messages = body.get("messages") or []
        since = (body.get("since") or "").strip() or None
        until = (body.get("until") or "").strip() or None

        # Modalità server-side: dir + file/files → parse + filtro span lato server.
        d = (body.get("dir") or "").strip()
        fnames = body.get("files") if isinstance(body.get("files"), list) else []
        single = (body.get("file") or "").strip()
        if single:
            fnames = [single] + [f for f in fnames if f != single]
        fnames = [str(f).strip() for f in fnames if str(f).strip()]
        if d and fnames and not messages:
            parser = _load_parser()
            messages = []
            for fname in fnames:
                path = _safe_resolve(d, fname)
                if path is None or not path.is_file():
                    return jsonify({"error": f"file non valido: {fname}"}), 400
                try:
                    with path.open("r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    recs = _filter_by_span(parser(data, set()), since, until)
                except Exception as exc:
                    return jsonify({"error": f"parse fallito ({fname}): {exc}"}), 422
                messages.extend(
                    {"author_name": r.get("author_name"), "content": r.get("content")}
                    for r in recs
                )
        elif messages and (since or until):
            # Filtra anche i messaggi pre-costruiti se hanno timestamp e span dato.
            messages = _filter_by_span(messages, since, until)

        if not scene_id or not isinstance(messages, list) or not messages:
            return jsonify({"error": "scene_id e messages[]/files richiesti"}), 400
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

    @app.route("/api/import/discord/live", methods=["POST"])
    def import_live():
        """Esegue un export DCE al volo per canale/i + finestra temporale.

        Body: {channel_ids: [...], since?: ISO, until?: ISO, out_dir?: str}
        Ritorna i metadati per-canale come /scan (dir + files), pronti per
        /preview e /to-scene. Se DCE non è installato, errore 503 pulito.
        """
        body = request.get_json(silent=True) or {}
        channel_ids = body.get("channel_ids")
        if not isinstance(channel_ids, list):
            single = body.get("channel_id")
            channel_ids = [single] if single else []
        channel_ids = [str(c).strip() for c in channel_ids if str(c).strip()]
        if not channel_ids:
            return jsonify({"error": "channel_ids[] richiesto"}), 400
        since = (body.get("since") or "").strip() or None
        until = (body.get("until") or "").strip() or None

        out_dir = (body.get("out_dir") or "").strip()
        if not out_dir:
            out_dir = tempfile.mkdtemp(prefix=f"dce-live-{int(time.time())}-")

        try:
            produced = discord_live.run_live_export(
                channel_ids, out_dir, after=since, before=until,
            )
        except discord_live.DceError as exc:
            return jsonify({"error": str(exc), "dce_available": discord_live.dce_available()}), 503

        files = []
        for f in produced:
            entry = {"file": f.name}
            try:
                with f.open("r", encoding="utf-8") as fh:
                    entry.update(_channel_meta(json.load(fh)))
            except Exception:
                pass
            files.append(entry)
        return jsonify({"dir": out_dir, "files": files, "exported": len(files)}), 200
