"""Contract test VG-2d (gap-review F2, scoperto dal RUN e2e row-count).

Il RUN reale ha migrato 303 scene ma solo 19/120 char. Root-cause: lo schema char
è ETEROGENEO — i draft auto-gen usano `id`, ma la maggioranza (card canon/private)
usa `slug` come identificatore, NON `id`. migrate_all (VG-2c) guardava solo `id` →
ha saltato ~100 char validi.

VG-2d: l'identificatore char = `d.get('id') or d.get('slug')`. Idempotente sull'id
risolto (dedup: es. due file con slug 'narrator' → 1 sola riga).
"""
import yaml

from app.db import get_db, init_schema
from app.scene_migrate import migrate_all


def _seed(tmp_path):
    scenes = tmp_path / "scenes"
    chars = tmp_path / "characters"
    scenes.mkdir()
    chars.mkdir()
    (chars / "by_id.yaml").write_text(
        yaml.safe_dump({"id": "cid1", "name": "ById", "type": "pc"}), encoding="utf-8"
    )
    (chars / "by_slug.yaml").write_text(
        yaml.safe_dump({"slug": "cslug1", "name": "BySlug"}), encoding="utf-8"
    )
    # due file con lo STESSO slug → una sola riga (idempotenza su id-risolto)
    (chars / "dup_a.yaml").write_text(
        yaml.safe_dump({"slug": "dupk", "name": "Dup A"}), encoding="utf-8"
    )
    (chars / "dup_b.yaml").write_text(
        yaml.safe_dump({"slug": "dupk", "name": "Dup B"}), encoding="utf-8"
    )
    return scenes, chars


def test_char_migrates_by_slug_when_no_id(tmp_path):
    scenes, chars = _seed(tmp_path)
    db = str(tmp_path / "t.db")
    init_schema(get_db(db))
    migrate_all(str(scenes), str(chars), db_path=db)
    conn = get_db(db)
    # il char con solo slug deve essere nel DB con id = slug
    row = conn.execute("SELECT name FROM characters WHERE id = ?", ("cslug1",)).fetchone()
    conn.close()
    assert row is not None and row[0] == "BySlug"


def test_char_dedup_on_resolved_id(tmp_path):
    scenes, chars = _seed(tmp_path)
    db = str(tmp_path / "t.db")
    init_schema(get_db(db))
    migrate_all(str(scenes), str(chars), db_path=db)
    conn = get_db(db)
    # 3 id-risolti unici: cid1, cslug1, dupk (i due 'dupk' = 1 riga sola)
    n = conn.execute("SELECT COUNT(*) FROM characters").fetchone()[0]
    n_dup = conn.execute("SELECT COUNT(*) FROM characters WHERE id = ?", ("dupk",)).fetchone()[0]
    conn.close()
    assert n == 3, f"attesi 3 char unici, trovati {n}"
    assert n_dup == 1, "lo slug duplicato deve dare 1 sola riga"
