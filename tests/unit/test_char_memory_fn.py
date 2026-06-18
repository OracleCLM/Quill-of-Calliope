"""GAP-43: test unitari per app/calliope_shell/char_memory — SQLite CRUD + FTS5."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

import app.calliope_shell.char_memory as cm


@pytest.fixture(autouse=True)
def _patch_db(tmp_path, monkeypatch):
    """Redirect _DB_PATH a un file temporaneo e inizializza lo schema."""
    db = tmp_path / "test_char_memory.db"
    monkeypatch.setattr(cm, "_DB_PATH", db)
    # Patch audit_trail e entity_linker per evitare effetti collaterali
    mock_audit = MagicMock()
    mock_extract = MagicMock(return_value=[])
    monkeypatch.setattr(
        "app.calliope_shell.char_memory.audit_trail",
        mock_audit,
        raising=False,
    )
    with (
        patch("app.calliope_shell.char_memory.audit_trail", mock_audit, create=True),
        patch(
            "app.calliope_shell.entity_linker.extract_entities_for_fact",
            mock_extract,
        ),
    ):
        cm.init_db()
        yield


# ── init_db ───────────────────────────────────────────────────────────────────


def test_init_db_creates_char_state(tmp_path):
    with cm._conn() as c:
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "char_state" in tables


def test_init_db_creates_char_facts_meta(tmp_path):
    with cm._conn() as c:
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "char_facts_meta" in tables


def test_init_db_idempotent():
    cm.init_db()
    cm.init_db()
    with cm._conn() as c:
        count = c.execute("SELECT count(*) FROM char_state").fetchone()[0]
    assert count == 0


# ── get_char ──────────────────────────────────────────────────────────────────


def test_get_char_returns_none_for_missing():
    assert cm.get_char("Aurora") is None


def test_get_char_returns_dict_after_upsert():
    with patch("app.calliope_shell.char_memory.audit_trail", MagicMock(), create=True):
        cm.upsert_char("Aurora", traits={"personality": ["coraggiosa"]})
    result = cm.get_char("Aurora")
    assert result is not None
    assert result["name"] == "Aurora"


def test_get_char_traits_deserialized():
    with patch("app.calliope_shell.char_memory.audit_trail", MagicMock(), create=True):
        cm.upsert_char("Mao", traits={"personality": ["vivace", "curiosa"]})
    result = cm.get_char("Mao")
    assert isinstance(result["traits"], dict)
    assert "personality" in result["traits"]


def test_get_char_entities_is_list():
    with patch("app.calliope_shell.char_memory.audit_trail", MagicMock(), create=True):
        cm.upsert_char("Kira")
    result = cm.get_char("Kira")
    assert isinstance(result["entities"], list)


# ── upsert_char ───────────────────────────────────────────────────────────────


def test_upsert_char_creates_new():
    with patch("app.calliope_shell.char_memory.audit_trail", MagicMock(), create=True):
        cm.upsert_char("Nova", last_action="arrivò alla taverna")
    result = cm.get_char("Nova")
    assert result["last_action"] == "arrivò alla taverna"


def test_upsert_char_updates_existing():
    with patch("app.calliope_shell.char_memory.audit_trail", MagicMock(), create=True):
        cm.upsert_char("Nova", last_action="azione 1")
        cm.upsert_char("Nova", last_action="azione 2")
    result = cm.get_char("Nova")
    assert result["last_action"] == "azione 2"


def test_upsert_char_preserves_traits_when_not_passed():
    with patch("app.calliope_shell.char_memory.audit_trail", MagicMock(), create=True):
        cm.upsert_char("Nova", traits={"class": "mago"})
        cm.upsert_char("Nova", last_action="incantesimo")
    result = cm.get_char("Nova")
    assert result["traits"].get("class") == "mago"


# ── list_chars ────────────────────────────────────────────────────────────────


def test_list_chars_empty():
    assert cm.list_chars() == []


def test_list_chars_returns_all():
    with patch("app.calliope_shell.char_memory.audit_trail", MagicMock(), create=True):
        cm.upsert_char("Aurora")
        cm.upsert_char("Mao")
    result = cm.list_chars()
    names = {r["name"] for r in result}
    assert "Aurora" in names and "Mao" in names


def test_list_chars_traits_summary():
    with patch("app.calliope_shell.char_memory.audit_trail", MagicMock(), create=True):
        cm.upsert_char("Aurora", traits={"personality": ["coraggiosa", "leale"]})
    result = cm.list_chars()
    row = next(r for r in result if r["name"] == "Aurora")
    assert "coraggiosa" in row["traits_summary"]


# ── delete_char ───────────────────────────────────────────────────────────────


def test_delete_char_returns_true():
    with patch("app.calliope_shell.char_memory.audit_trail", MagicMock(), create=True):
        cm.upsert_char("Efimero")
    assert cm.delete_char("Efimero") is True


def test_delete_char_removes_entry():
    with patch("app.calliope_shell.char_memory.audit_trail", MagicMock(), create=True):
        cm.upsert_char("Efimero")
    cm.delete_char("Efimero")
    assert cm.get_char("Efimero") is None


def test_delete_char_returns_false_for_missing():
    assert cm.delete_char("Inesistente") is False


# ── append_fact ───────────────────────────────────────────────────────────────


def test_append_fact_returns_id():
    with patch("app.calliope_shell.char_memory.audit_trail", MagicMock(), create=True):
        with patch("app.calliope_shell.entity_linker.extract_entities_for_fact", return_value=[]):
            fid = cm.append_fact("Aurora", "Ha trovato la spada magica", scope="L1")
    assert fid is not None and isinstance(fid, str)


def test_append_fact_l0_protected():
    with patch("app.calliope_shell.char_memory.audit_trail", MagicMock(), create=True):
        fid = cm.append_fact("Aurora", "fatto protetto", scope="L0")
    assert fid is None


def test_append_fact_invalid_scope_rejected():
    with patch("app.calliope_shell.char_memory.audit_trail", MagicMock(), create=True):
        fid = cm.append_fact("Aurora", "fatto", scope="L99")
    assert fid is None


def test_append_fact_persists():
    with patch("app.calliope_shell.char_memory.audit_trail", MagicMock(), create=True):
        with patch("app.calliope_shell.entity_linker.extract_entities_for_fact", return_value=[]):
            cm.append_fact("Aurora", "fatto persistito", scope="L1")
    facts = cm.get_facts("Aurora")
    assert any("persistito" in f["fact_text"] for f in facts)


# ── replace_fact ──────────────────────────────────────────────────────────────


def test_replace_fact_l0_protected():
    result = cm.replace_fact("Aurora", "x", "y", scope="L0")
    assert result["success"] is False


def test_replace_fact_invalid_scope():
    result = cm.replace_fact("Aurora", "x", "y", scope="INVALID")
    assert result["success"] is False


def test_replace_fact_replaces_text():
    with patch("app.calliope_shell.char_memory.audit_trail", MagicMock(), create=True):
        with patch("app.calliope_shell.entity_linker.extract_entities_for_fact", return_value=[]):
            cm.append_fact("Aurora", "possiede spada vecchia", scope="L1")
    with patch("app.calliope_shell.char_memory.audit_trail", MagicMock(), create=True):
        result = cm.replace_fact("Aurora", "spada vecchia", "spada magica", scope="L1")
    assert result["success"] is True
    assert result["replaced"] >= 1
    facts = cm.get_facts("Aurora")
    assert any("spada magica" in f["fact_text"] for f in facts)


def test_replace_fact_no_match_returns_zero():
    with patch("app.calliope_shell.char_memory.audit_trail", MagicMock(), create=True):
        result = cm.replace_fact("Aurora", "stringa inesistente", "nuovo", scope="L1")
    assert result["success"] is True
    assert result["replaced"] == 0


# ── get_facts ─────────────────────────────────────────────────────────────────


def test_get_facts_empty_for_new_char():
    assert cm.get_facts("NuovoChar") == []


def test_get_facts_filtered_by_scope():
    with patch("app.calliope_shell.char_memory.audit_trail", MagicMock(), create=True):
        with patch("app.calliope_shell.entity_linker.extract_entities_for_fact", return_value=[]):
            cm.append_fact("Aurora", "fatto L1", scope="L1")
            cm.append_fact("Aurora", "fatto L2", scope="L2")
    l1_facts = cm.get_facts("Aurora", scope="L1")
    l2_facts = cm.get_facts("Aurora", scope="L2")
    assert all(f["scope"] == "L1" for f in l1_facts)
    assert all(f["scope"] == "L2" for f in l2_facts)


def test_get_facts_all_scopes_when_none():
    with patch("app.calliope_shell.char_memory.audit_trail", MagicMock(), create=True):
        with patch("app.calliope_shell.entity_linker.extract_entities_for_fact", return_value=[]):
            cm.append_fact("Aurora", "L1", scope="L1")
            cm.append_fact("Aurora", "L2", scope="L2")
    facts = cm.get_facts("Aurora")
    scopes = {f["scope"] for f in facts}
    assert "L1" in scopes and "L2" in scopes


# ── _fts_escape ───────────────────────────────────────────────────────────────


def test_fts_escape_empty_query():
    assert cm._fts_escape("") == '""'


def test_fts_escape_single_token():
    result = cm._fts_escape("drago")
    assert '"drago"' in result


def test_fts_escape_prefix_for_long_token():
    result = cm._fts_escape("addestrare")
    assert '"addes"*' in result


def test_fts_escape_multiple_tokens_joined_or():
    result = cm._fts_escape("spada magica")
    assert " OR " in result


def test_fts_escape_strips_quotes():
    result = cm._fts_escape('parola"con"virgolette')
    assert '"' not in result.replace('"', "").replace("*", "")


# ── retrieve_multi_signal ─────────────────────────────────────────────────────


def test_retrieve_multi_signal_empty_returns_empty():
    result = cm.retrieve_multi_signal("Aurora", "drago magico")
    assert isinstance(result, list)


def test_retrieve_multi_signal_returns_inserted_fact():
    with patch("app.calliope_shell.char_memory.audit_trail", MagicMock(), create=True):
        with patch("app.calliope_shell.entity_linker.extract_entities_for_fact", return_value=[]):
            cm.append_fact("Aurora", "Aurora porta una spada leggendaria", scope="L1")
    result = cm.retrieve_multi_signal("Aurora", "spada")
    assert isinstance(result, list)


def test_retrieve_multi_signal_top_k_respected():
    with patch("app.calliope_shell.char_memory.audit_trail", MagicMock(), create=True):
        with patch("app.calliope_shell.entity_linker.extract_entities_for_fact", return_value=[]):
            for i in range(10):
                cm.append_fact("Aurora", f"fatta numero {i} castelli draghi elfi", scope="L1")
    result = cm.retrieve_multi_signal("Aurora", "castelli draghi", top_k=3)
    assert len(result) <= 3
