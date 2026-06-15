"""Contract test VG-1b (gap-review F1, chiusura PIENA lato generazione).

VG-1 ha dato `build_scene_context` (DB-aware). MA `/api/messages/next` e
`/api/messages/continue` costruiscono ancora il contesto-scena con un glob
flat-YAML inline (server.py ~1036-1042 e ~1115-1123) → il draft-gen NON vede
mai il DB scene-as-chat. Questo è il cuore del FATALE F1.

VG-1b introduce `resolve_scene_context(scene_id, db_path=None, scenes_dir=None)`:
  - DB-FIRST: se la scena esiste nel DB → ritorna build_scene_context (titolo + messaggi).
  - FALLBACK-YAML: se non è nel DB ma c'è un .yaml in scenes_dir → contesto flat-YAML
    (compat retro col vecchio path durante la migrazione).
  - VUOTO: né DB né YAML → "".
E le due route DEVONO usarlo (guard di wiring) — non più il glob inline.
"""
from pathlib import Path

import yaml

from app.db import get_db, init_schema, new_id
from app.db.messages import add_message
from app.scene_context import resolve_scene_context


def _seed_db(tmp_path):
    p = tmp_path / "t.db"
    conn = get_db(p)
    init_schema(conn)
    sid = new_id()
    conn.execute("INSERT INTO scenes (id, title) VALUES (?, ?)", (sid, "La Taverna del Drago"))
    conn.commit()
    add_message(conn, scene_id=sid, author_name="Aelar", content_original="Benvenuto.", position_order=0)
    conn.close()
    return str(p), sid


def _seed_yaml(tmp_path):
    d = tmp_path / "scenes"
    d.mkdir()
    (d / "foresta-incantata.yaml").write_text(
        yaml.safe_dump(
            {"title": "Foresta Incantata", "summary": "Un bosco antico.", "participants": ["Elora", "Kael"]}
        ),
        encoding="utf-8",
    )
    return d


def test_resolve_prefers_db(tmp_path):
    db, sid = _seed_db(tmp_path)
    ctx = resolve_scene_context(sid, db_path=db, scenes_dir=_seed_yaml(tmp_path))
    # Deve usare il DB (titolo + messaggio), NON il YAML.
    assert "La Taverna del Drago" in ctx
    assert "Aelar" in ctx and "Benvenuto." in ctx


def test_resolve_falls_back_to_yaml(tmp_path):
    db, _ = _seed_db(tmp_path)
    scenes_dir = _seed_yaml(tmp_path)
    # scene_id presente SOLO come YAML, non nel DB → fallback.
    ctx = resolve_scene_context("foresta-incantata", db_path=db, scenes_dir=scenes_dir)
    assert "Foresta Incantata" in ctx


def test_resolve_empty_when_neither(tmp_path):
    db, _ = _seed_db(tmp_path)
    assert resolve_scene_context("nessuna-scena", db_path=db, scenes_dir=tmp_path / "scenes") == ""


def test_routes_wire_resolve_scene_context():
    """Guard di wiring (anti gap composto): le route draft-gen DEVONO chiamare
    resolve_scene_context, non più il glob flat-YAML inline."""
    src = (
        Path(__file__).parents[2] / "app" / "calliope_shell" / "server.py"
    ).read_text(encoding="utf-8")
    assert "resolve_scene_context(" in src, "server.py non cabla resolve_scene_context"
    # Le due route non devono più costruire scene_ctx con il glob inline _SCENES_DIR.
    assert src.count("resolve_scene_context(") >= 2, "entrambe le route devono usarlo"
