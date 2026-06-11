"""Contract test VG-3a (disciplina-test): get_db rispetta l'env CALLIOPE_DB_PATH.

Il verify-harness (.planning/fe_browser_verify.py) seminava il DB di PRODUZIONE
(data/calliope.db) perché get_db non aveva override → ha inquinato il prod con
seed 'Scena Verify'/'Aelar' (gap F2). Per isolare l'harness, il server (subprocess)
deve poter puntare a un DB temporaneo via env CALLIOPE_DB_PATH; le route chiamano
get_db() senza path → deve leggere l'env a ogni chiamata quando path è None.

Produzione (env non settato) → default invariato.
"""
import app.db as dbmod


def _db_file(conn):
    return conn.execute("PRAGMA database_list").fetchone()[2]


def test_get_db_respects_env_when_no_path(monkeypatch, tmp_path):
    p = tmp_path / "env_override.db"
    monkeypatch.setenv("CALLIOPE_DB_PATH", str(p))
    conn = dbmod.get_db()  # nessun arg → deve usare l'env
    f = _db_file(conn)
    conn.close()
    assert str(f).endswith("env_override.db"), f"get_db() ha ignorato l'env: {f}"


def test_get_db_default_when_env_absent(monkeypatch):
    monkeypatch.delenv("CALLIOPE_DB_PATH", raising=False)
    conn = dbmod.get_db()
    f = _db_file(conn)
    conn.close()
    # senza env → default di produzione (data/calliope.db)
    assert str(f).endswith("data/calliope.db"), f"default di produzione cambiato: {f}"


def test_explicit_path_still_wins(monkeypatch, tmp_path):
    # un path esplicito ha priorità sull'env (back-compat con i test esistenti)
    monkeypatch.setenv("CALLIOPE_DB_PATH", str(tmp_path / "env.db"))
    explicit = tmp_path / "explicit.db"
    conn = dbmod.get_db(str(explicit))
    f = _db_file(conn)
    conn.close()
    assert str(f).endswith("explicit.db")
