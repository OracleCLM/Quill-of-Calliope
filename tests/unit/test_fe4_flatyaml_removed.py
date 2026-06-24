"""
Acceptance test FE-4 (WI_FRONTEND_DB_MIGRATION 2026-06-11).

Verifica che le route flat-YAML legacy siano state rimosse da create_app()
e che le route DB corrispondenti siano ancora presenti (regression guard).

Decisione operatore 2026-06-11: migrazione COMPLETA, NO fallback.
"""
from app.calliope_shell.server import create_app


def _live_rules():
    app, _ = create_app()
    return {str(r) for r in app.url_map.iter_rules()}


_REMOVED_ROUTES = {
    "/api/scenes",
    "/api/scenes/<scene_id>",
    "/api/messages/recent",
}


def test_fe4_flat_yaml_routes_absent():
    rules = _live_rules()
    still_present = _REMOVED_ROUTES & rules
    assert not still_present, f"Route flat-YAML legacy ancora registrate: {sorted(still_present)}"


def test_fe4_db_scene_routes_still_present():
    rules = _live_rules()
    required = {"/api/db/scenes", "/api/db/scenes/<scene_id>"}
    missing = required - rules
    assert not missing, f"Route DB mancanti: {sorted(missing)}"
