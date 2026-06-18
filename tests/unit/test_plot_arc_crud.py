"""GAP-50: test per create_arc / get_arc / list_arcs / append_scene in plot_arc.py."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

import app.calliope_shell.plot_arc as pa


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path):
    db = tmp_path / "arc_test.db"
    monkeypatch.setattr(pa, "DB_PATH", db)
    # Evita import reale di audit_trail
    monkeypatch.setattr(
        "app.calliope_shell.plot_arc.audit_trail",
        MagicMock(),
        raising=False,
    )
    pa.init_db()
    yield


# ── create_arc ────────────────────────────────────────────────────────────────


def test_create_arc_returns_dict():
    arc = pa.create_arc("arc-1", "La Grande Guerra", ["Aurora", "Mao"])
    assert isinstance(arc, dict)


def test_create_arc_arc_id_matches():
    arc = pa.create_arc("arc-2", "Titolo", [])
    assert arc["arc_id"] == "arc-2"


def test_create_arc_title_matches():
    arc = pa.create_arc("arc-3", "Epopea", [])
    assert arc["title"] == "Epopea"


def test_create_arc_chars_stored():
    arc = pa.create_arc("arc-4", "T", ["Kira", "Zoe"])
    assert "Kira" in arc["chars"]
    assert "Zoe" in arc["chars"]


def test_create_arc_empty_chars():
    arc = pa.create_arc("arc-5", "T", [])
    assert arc["chars"] == []


def test_create_arc_is_retrievable():
    pa.create_arc("arc-6", "Cercami", [])
    found = pa.get_arc("arc-6")
    assert found is not None
    assert found["title"] == "Cercami"


def test_create_arc_replace_existing():
    pa.create_arc("arc-7", "Vecchio", ["A"])
    arc = pa.create_arc("arc-7", "Nuovo", ["B"])
    assert arc["title"] == "Nuovo"
    assert "B" in arc["chars"]


# ── get_arc ───────────────────────────────────────────────────────────────────


def test_get_arc_none_for_missing():
    assert pa.get_arc("inesistente") is None


def test_get_arc_returns_dict_with_scenes():
    pa.create_arc("arc-8", "T", [])
    arc = pa.get_arc("arc-8")
    assert "scenes" in arc
    assert arc["scenes"] == []


def test_get_arc_status_default_active():
    pa.create_arc("arc-9", "T", [])
    arc = pa.get_arc("arc-9")
    assert arc["status"] == "active"


def test_get_arc_chars_are_list():
    pa.create_arc("arc-10", "T", ["X"])
    arc = pa.get_arc("arc-10")
    assert isinstance(arc["chars"], list)


# ── list_arcs ─────────────────────────────────────────────────────────────────


def test_list_arcs_empty():
    assert pa.list_arcs() == []


def test_list_arcs_returns_all():
    pa.create_arc("la-1", "A", [])
    pa.create_arc("la-2", "B", [])
    arcs = pa.list_arcs()
    assert len(arcs) == 2


def test_list_arcs_filter_by_status_active():
    pa.create_arc("lf-1", "Attivo", [])
    arcs = pa.list_arcs(status="active")
    assert len(arcs) == 1


def test_list_arcs_filter_status_no_match():
    pa.create_arc("lf-2", "T", [])
    arcs = pa.list_arcs(status="closed")
    assert arcs == []


def test_list_arcs_each_has_arc_id():
    pa.create_arc("lm-1", "T", [])
    for arc in pa.list_arcs():
        assert "arc_id" in arc


# ── append_scene ──────────────────────────────────────────────────────────────


@pytest.fixture
def arc_with_file(tmp_path):
    pa.create_arc("as-arc", "Arc Scena", ["Mao"])
    scene_file = tmp_path / "scene01.md"
    scene_file.write_text("# Scena 1\nIl drago attacca il villaggio.\n", encoding="utf-8")
    return "as-arc", str(scene_file)


def test_append_scene_returns_dict(arc_with_file):
    arc_id, path = arc_with_file
    result = pa.append_scene(arc_id, path, scene_summary="Drago attacca.")
    assert isinstance(result, dict)


def test_append_scene_arc_id_in_result(arc_with_file):
    arc_id, path = arc_with_file
    result = pa.append_scene(arc_id, path, scene_summary="Sommario.")
    assert result["arc_id"] == arc_id


def test_append_scene_scene_order_zero_first(arc_with_file):
    arc_id, path = arc_with_file
    result = pa.append_scene(arc_id, path, scene_summary="S.")
    assert result["scene_order"] == 0


def test_append_scene_order_increments(tmp_path):
    pa.create_arc("incr-arc", "T", [])
    f1 = tmp_path / "s1.md"
    f2 = tmp_path / "s2.md"
    f1.write_text("Scena uno.", encoding="utf-8")
    f2.write_text("Scena due.", encoding="utf-8")
    r1 = pa.append_scene("incr-arc", str(f1), scene_summary="S1")
    r2 = pa.append_scene("incr-arc", str(f2), scene_summary="S2")
    assert r2["scene_order"] == r1["scene_order"] + 1


def test_append_scene_scene_id_contains_arc_id(arc_with_file):
    arc_id, path = arc_with_file
    result = pa.append_scene(arc_id, path, scene_summary="S.")
    assert arc_id in result["scene_id"]


def test_append_scene_appears_in_get_arc(arc_with_file):
    arc_id, path = arc_with_file
    pa.append_scene(arc_id, path, scene_summary="Sommario visibile.")
    arc = pa.get_arc(arc_id)
    assert len(arc["scenes"]) == 1
    assert arc["scenes"][0]["scene_summary"] == "Sommario visibile."


def test_append_scene_missing_file_returns_empty(monkeypatch):
    pa.create_arc("miss-arc", "T", [])
    result = pa.append_scene("miss-arc", "/tmp/inesistente_xyz.md", scene_summary="S.")
    assert result == {}


def test_append_scene_auto_summary_via_groq(monkeypatch, tmp_path):
    pa.create_arc("groq-arc", "T", [])
    f = tmp_path / "groq_scene.md"
    f.write_text("Azione epica nella foresta.", encoding="utf-8")
    monkeypatch.setattr(pa, "_groq_ask", lambda *a, **kw: "Sommario groq mock.")
    result = pa.append_scene("groq-arc", str(f))
    assert result["scene_summary"] == "Sommario groq mock."


def test_append_scene_groq_empty_uses_fallback(monkeypatch, tmp_path):
    pa.create_arc("fb-arc", "T", [])
    f = tmp_path / "fb_scene.md"
    f.write_text("Testo scena.", encoding="utf-8")
    monkeypatch.setattr(pa, "_groq_ask", lambda *a, **kw: "")
    result = pa.append_scene("fb-arc", str(f))
    assert result["scene_summary"] == "No summary available."
