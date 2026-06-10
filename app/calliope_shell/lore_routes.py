from flask import jsonify, request
from app.calliope_shell.lore_kb import LoreStore, LoreEntry, LORE_CATEGORIES


def register_lore_routes(app, *, store_path=None):
    @app.route("/api/lore/categories", methods=["GET"])
    def lore_categories():
        return jsonify({"categories": LORE_CATEGORIES})

    @app.route("/api/lore/entries", methods=["GET"])
    def lore_entries_list():
        store = LoreStore(path=store_path)
        category = request.args.get("category")
        entries = store.list_by_category(category if category else None)
        return jsonify({"entries": [e.to_dict() for e in entries]})

    @app.route("/api/lore/entries/<entry_id>", methods=["GET"])
    def lore_entry_get(entry_id: str):
        store = LoreStore(path=store_path)
        entry = store.get_entry(entry_id)
        if entry is None:
            return jsonify({"error": "lore entry not found"}), 404
        return jsonify(entry.to_dict())

    @app.route("/api/lore/entries", methods=["POST"])
    def lore_entry_create():
        store = LoreStore(path=store_path)
        data = request.get_json(silent=True) or {}
        title = str(data.get("title") or "").strip()
        if not title:
            return jsonify({"error": "title required"}), 400

        def coerce_list(value):
            return list(value) if isinstance(value, (list, tuple)) else []

        def coerce_dict(value):
            return dict(value) if isinstance(value, dict) else {}

        def coerce_int(value, fallback=100):
            try:
                return int(value)
            except (TypeError, ValueError):
                return fallback

        entry = LoreEntry(
            id="",
            title=title,
            category=data.get("category", "other"),
            keys=coerce_list(data.get("keys", [])),
            content=data.get("content", ""),
            insertion_order=coerce_int(data.get("insertion_order", 100)),
            scope=data.get("scope", "global"),
            constant=bool(data.get("constant", False)),
            extensions=coerce_dict(data.get("extensions", {})),
        )
        created = store.add_entry(entry)
        return jsonify(created.to_dict()), 201

    @app.route("/api/lore/entries/<entry_id>", methods=["PUT"])
    def lore_entry_update(entry_id: str):
        store = LoreStore(path=store_path)
        data = request.get_json(silent=True) or {}
        updatable_fields = {}
        if "title" in data:
            updatable_fields["title"] = data["title"]
        if "category" in data:
            updatable_fields["category"] = data["category"]
        if "keys" in data:
            updatable_fields["keys"] = (
                list(data["keys"])
                if isinstance(data["keys"], (list, tuple))
                else []
            )
        if "content" in data:
            updatable_fields["content"] = data["content"]
        if "insertion_order" in data:
            try:
                updatable_fields["insertion_order"] = int(
                    data["insertion_order"]
                )
            except (TypeError, ValueError):
                updatable_fields["insertion_order"] = 100
        if "scope" in data:
            updatable_fields["scope"] = data["scope"]
        if "constant" in data:
            updatable_fields["constant"] = bool(data["constant"])
        if "extensions" in data:
            updatable_fields["extensions"] = (
                dict(data["extensions"])
                if isinstance(data["extensions"], dict)
                else {}
            )
        updated = store.update_entry(entry_id, **updatable_fields)
        if updated is None:
            return jsonify({"error": "lore entry not found"}), 404
        return jsonify(updated.to_dict())

    @app.route("/api/lore/entries/<entry_id>", methods=["DELETE"])
    def lore_entry_delete(entry_id: str):
        store = LoreStore(path=store_path)
        if store.delete_entry(entry_id):
            return jsonify({"deleted": True})
        return jsonify({"error": "lore entry not found"}), 404
