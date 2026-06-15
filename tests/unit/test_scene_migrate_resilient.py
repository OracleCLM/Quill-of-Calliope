"""Contract test VG-2c (gap-review F2, scoperto dal RUN e2e su dati reali).

Il RUN di migrate_all sui 332+122 YAML reali ha trovato 31 file MALFORMATI
(draft auto-generati con escaping rotto: ParserError). migrate_all abortiva sul
primo file malformato → ZERO dati migrati. VG-2c rende la migrazione RESILIENTE:
salta i file non-parsabili, li raccoglie in `skipped`, e migra tutto il resto.

Confine: è la lezione "verifica il flusso e2e composto, non le unità isolate" —
gli unit-test su fixture pulite (VG-2b) non potevano cogliere i dati-reali rotti.
"""
import yaml

from app.db import get_db, init_schema
from app.scene_migrate import migrate_all


def _seed_mixed(tmp_path):
    scenes = tmp_path / "scenes"
    chars = tmp_path / "characters"
    scenes.mkdir()
    chars.mkdir()
    # 2 scene valide
    (scenes / "scene_a.yaml").write_text(
        yaml.safe_dump({"scene_id": "sa", "title": "Scena A"}), encoding="utf-8"
    )
    (scenes / "scene_b.yaml").write_text(
        yaml.safe_dump({"scene_id": "sb", "title": "Scena B"}), encoding="utf-8"
    )
    # 1 scena MALFORMATA (flow-sequence non chiusa → yaml.YAMLError)
    (scenes / "scene_bad.yaml").write_text('title: [unterminated\nscene_id: sbad\n', encoding="utf-8")
    # 2 char validi
    (chars / "c_a.yaml").write_text(
        yaml.safe_dump({"id": "ca", "name": "Char A", "type": "pc"}), encoding="utf-8"
    )
    (chars / "c_b.yaml").write_text(
        yaml.safe_dump({"id": "cb", "name": "Char B", "type": "npc"}), encoding="utf-8"
    )
    # 1 char MALFORMATO
    (chars / "c_bad.yaml").write_text('name: "unterminated\nid: cbad\n', encoding="utf-8")
    return scenes, chars


def _counts(db_path):
    conn = get_db(db_path)
    s = conn.execute("SELECT COUNT(*) FROM scenes").fetchone()[0]
    c = conn.execute("SELECT COUNT(*) FROM characters").fetchone()[0]
    conn.close()
    return s, c


def test_migrate_all_skips_malformed_not_aborts(tmp_path):
    scenes, chars = _seed_mixed(tmp_path)
    db = str(tmp_path / "t.db")
    init_schema(get_db(db))
    # NON deve sollevare: deve migrare i validi e saltare i rotti.
    res = migrate_all(str(scenes), str(chars), db_path=db)
    assert res["scenes"] == 2, "deve migrare le 2 scene valide"
    assert res["characters"] == 2, "deve migrare i 2 char validi"
    assert _counts(db) == (2, 2)


def test_migrate_all_reports_skipped(tmp_path):
    scenes, chars = _seed_mixed(tmp_path)
    db = str(tmp_path / "t.db")
    init_schema(get_db(db))
    res = migrate_all(str(scenes), str(chars), db_path=db)
    # I file malformati sono raccolti in 'skipped' (lista di path), non persi in silenzio.
    assert "skipped" in res
    assert len(res["skipped"]) == 2
    assert any("scene_bad" in str(p) for p in res["skipped"])
    assert any("c_bad" in str(p) for p in res["skipped"])
