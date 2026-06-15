"""Contract test VG-1c (gap-review F1, scoperto dall'E2E REALE — bug migration-codepath).

L'e2e (test-client su /api/messages/next + /api/draft con scena-DB reale) ha dato 500:
`sqlite3.OperationalError: no such table: scenes`. Root-cause: le route draft-gen chiamano
resolve_scene_context(scene_id, scenes_dir=...) SENZA db_path → build_scene_context fa
get_db(None) → sqlite3.connect("None") apre un file vuoto chiamato "None" (footgun) invece
del DB di produzione → la tabella scenes non c'è.

Lezione: row-count verde + unit verdi (che passavano db_path esplicito) NON bastano; il
codepath reale della route passa None. get_db deve trattare None come il default.
"""
import app.db as dbmod


def _db_file(conn):
    # PRAGMA database_list: (seq, name, file) — file della connessione 'main'
    return conn.execute("PRAGMA database_list").fetchone()[2]


def test_get_db_none_uses_default_not_none_file():
    conn_none = dbmod.get_db(None)
    p_none = _db_file(conn_none)
    conn_none.close()
    # NON deve aprire un file chiamato 'None'
    assert not str(p_none).endswith("None"), f"get_db(None) ha aperto un file 'None': {p_none}"


def test_get_db_none_same_as_default():
    conn_none = dbmod.get_db(None)
    conn_def = dbmod.get_db()
    p_none = _db_file(conn_none)
    p_def = _db_file(conn_def)
    conn_none.close()
    conn_def.close()
    # get_db(None) deve puntare allo STESSO file di get_db() (il default CALLIOPE_DB_PATH)
    assert p_none == p_def
