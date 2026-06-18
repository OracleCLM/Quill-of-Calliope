"""
Smoke test wiring server↔DB (WI-9, gap-list 2026-06-08).

Root-cause storica del P5 "false-DONE": il layer DB scene-as-chat era testato in
isolamento ma `server.py:create_app()` non registrava le route → la dashboard
serviva ancora il vecchio modello flat-YAML. Questo test blinda il WIRING:
verifica che le route `/api/db/*` siano effettivamente nella url_map dell'app
reale prodotta da create_app(), così un refactor non può silenziosamente
sganciarle senza far fallire la suite.
"""

from app.calliope_shell.server import create_app

# Route DB-backed che DEVONO essere registrate da create_app() (campione
# rappresentativo che copre scene-CRUD, messaggi, roster, arc — incluse le
# route aggiunte 2026-06-11: move, arc-assign, role PATCH, arcs CRUD, /api/write).
_REQUIRED_DB_RULES = {
    "/api/db/scenes",
    "/api/db/scenes/<scene_id>",
    "/api/db/scenes/<scene_id>/messages",
    "/api/db/scenes/<scene_id>/messages/insert",
    "/api/db/scenes/<scene_id>/characters",
    "/api/db/scenes/<scene_id>/characters/<character_id>",
    "/api/db/scenes/<scene_id>/arc",
    "/api/db/scenes/merge",
    "/api/db/messages/<message_id>",
    "/api/db/messages/<message_id>/move",
    "/api/db/arcs",
    "/api/db/arcs/<arc_id>",
    "/api/db/arcs/<arc_id>/scenes",
    "/api/write",
    "/api/db/messages/recent",
}


def _live_rules():
    app, _ = create_app()
    return {str(r) for r in app.url_map.iter_rules()}


def test_db_routes_registered_in_create_app():
    rules = _live_rules()
    missing = _REQUIRED_DB_RULES - rules
    assert not missing, f"Route DB non cablate in create_app(): {sorted(missing)}"


def test_db_layer_has_meaningful_route_count():
    # Sanity: il layer DB espone molti path distinti (~19 attuali). Soglia ≥15
    # difende contro una registrazione parziale/silenziosamente troncata (una
    # registrazione monca cadrebbe a poche unità) senza essere fragile all'aggiunta
    # o rimozione di una singola route.
    db_rules = {r for r in _live_rules() if r.startswith("/api/db/")}
    assert len(db_rules) >= 15, f"Solo {len(db_rules)} path /api/db/ — wiring incompleto?"
