"""TPA1-TPA10 — R-CALLIOPE-S-PLOT-ARC test suite."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from app.calliope_shell import plot_arc


@pytest.fixture(autouse=True)
def _tmp_db(tmp_path, monkeypatch):
    """Each test gets its own DB so state doesn't leak."""
    db = tmp_path / "test_char_memory.db"
    monkeypatch.setattr(plot_arc, "DB_PATH", db)
    plot_arc.init_db()
    yield db


def _make_scene_file(tmp_path: Path, body: str = "Aurora entered the vault. Something was missing.") -> Path:
    p = tmp_path / "scene.md"
    p.write_text(
        f"# Scene: mystery_investigation\n"
        f"**Tier**: cerebras | **Provider**: cerebras | **Latency**: 100ms | **Mode**: Generated\n\n"
        f"{body}\n\n---\n_Generated 2026-05-20_\n",
        encoding="utf-8",
    )
    return p


# TPA1 — schema migration idempotent (init_db x2 safe)
def test_tpa1_schema_idempotent():
    plot_arc.init_db()
    plot_arc.init_db()  # second call must not raise
    arcs = plot_arc.list_arcs()
    assert isinstance(arcs, list)


# TPA2 — create_arc + get_arc
def test_tpa2_create_and_retrieve():
    arc = plot_arc.create_arc("test-arc-1", "Aurora vs Cult", ["Aurora", "Philly"])
    assert arc["arc_id"] == "test-arc-1"
    retrieved = plot_arc.get_arc("test-arc-1")
    assert retrieved is not None
    assert retrieved["title"] == "Aurora vs Cult"
    assert "Aurora" in retrieved["chars"]
    assert retrieved["scenes"] == []


# TPA3 — append_scene + auto-summary (mock LLM)
def test_tpa3_append_scene_auto_summary(tmp_path):
    plot_arc.create_arc("arc-append", "Test Arc", ["Aurora"])
    scene_file = _make_scene_file(tmp_path)
    with patch.object(plot_arc, "_groq_ask", return_value="Aurora explored a dark vault."):
        result = plot_arc.append_scene("arc-append", str(scene_file))
    assert result["scene_order"] == 0
    assert result["scene_summary"] == "Aurora explored a dark vault."
    arc = plot_arc.get_arc("arc-append")
    assert len(arc["scenes"]) == 1


# TPA4 — regenerate_summary aggregates scene summaries
def test_tpa4_regenerate_summary(tmp_path):
    plot_arc.create_arc("arc-sum", "Summary Arc", ["Aurora"])
    # Use explicit summary to skip LLM call in append
    f1 = tmp_path / "f1.md"
    f1.write_text("# Scene\n**Tier**: x\n\nScene one body.\n\n---\nend\n", encoding="utf-8")
    f2 = tmp_path / "f2.md"
    f2.write_text("# Scene\n**Tier**: x\n\nScene two body.\n\n---\nend\n", encoding="utf-8")
    plot_arc.append_scene("arc-sum", str(f1), scene_summary="Aurora found clues in the vault.")
    plot_arc.append_scene("arc-sum", str(f2), scene_summary="Philly confronted the vampire elder.")
    with patch.object(plot_arc, "_groq_ask", return_value="3-line arc summary here."):
        summary = plot_arc.regenerate_summary("arc-sum")
    assert "summary" in summary.lower() or len(summary) > 5
    arc = plot_arc.get_arc("arc-sum")
    assert arc["summary"] == "3-line arc summary here."


# TPA5 — detect_open_threads finds unresolved entities
def test_tpa5_detect_open_threads(tmp_path):
    plot_arc.create_arc("arc-threads", "Thread Arc", ["Aurora"])
    f = tmp_path / "t.md"
    f.write_text("# Scene\n**Tier**: x\n\nAurora is seeking the missing Elder. Something unknown lurks.\n\n---\nend\n", encoding="utf-8")
    plot_arc.append_scene("arc-threads", str(f), scene_summary="Aurora is seeking the missing Elder. Something unknown lurks.")
    threads = plot_arc.detect_open_threads("arc-threads")
    assert isinstance(threads, list)
    # Should detect 'seeking', 'missing', 'unknown' as unresolved events
    types = {t["type"] for t in threads}
    assert "event" in types or "character" in types


# TPA6 — propose_next_scene returns valid scene_type + prompt_seed
def test_tpa6_propose_next_scene(tmp_path):
    plot_arc.create_arc("arc-next", "Next Scene Arc", ["Aurora"])
    f = tmp_path / "s.md"
    f.write_text("# Scene\n**Tier**: x\n\nAurora investigates the basement.\n\n---\nend\n", encoding="utf-8")
    plot_arc.append_scene("arc-next", str(f), scene_summary="Aurora investigates the basement.")
    with patch.object(plot_arc, "_groq_ask", return_value="scene_type: mystery_investigation\nprompt: Philly discovers a hidden door in the vault, leading deeper underground."):
        result = plot_arc.propose_next_scene("arc-next", hint="Philly finds evidence")
    assert result.get("scene_type") in plot_arc._VALID_SCENE_TYPES
    assert len(result.get("prompt_seed", "")) > 5
    assert result.get("hint_used") == "Philly finds evidence"


# TPA7 — search_arcs_by_topic (degrades gracefully if ChromaDB unavailable)
def test_tpa7_search_arcs_by_topic():
    plot_arc.create_arc("arc-search", "Vampire Cult Arc", ["Aurora"])
    results = plot_arc.search_arcs_by_topic("vampire cult")
    assert isinstance(results, list)
    # Either found results or empty list (ChromaDB fallback OK)


# TPA8 — Flask /api/arc CRUD 200 OK
def test_tpa8_flask_arc_crud():
    from app.calliope_shell.server import create_app  # noqa: PLC0415
    app, _ = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        # POST create
        resp = client.post("/api/arc", json={"arc_id": "flask-arc", "title": "Test Arc", "chars": ["Aurora"]}, content_type="application/json")
        assert resp.status_code == 201
        # GET list
        resp = client.get("/api/arc")
        assert resp.status_code == 200
        data = resp.get_json()
        assert any(a["arc_id"] == "flask-arc" for a in data)
        # GET single
        resp = client.get("/api/arc/flask-arc")
        assert resp.status_code == 200
        assert resp.get_json()["title"] == "Test Arc"


# TPA9 — generate_scene.py --arc flag: arc_context_prefix is built when arc exists
def test_tpa9_generate_scene_arc_flag(tmp_path):
    import generate_scene as gs  # noqa: PLC0415

    plot_arc.create_arc("arc-gen", "Gen Arc", ["Aurora"])
    output_file = tmp_path / "arc_scene.md"

    with (
        patch.object(gs, "dispatch_to_tier", return_value="Aurora fought the vampire.") as mock_dispatch,
        patch.object(gs, "route_scene", return_value={"tier": "cerebras_workhorse", "provider": "cerebras"}),
        patch.object(gs, "load_config", return_value={}),
        patch.object(gs, "_publish_emotion"),
        patch("app.calliope_shell.plot_arc.get_arc", return_value={
            "arc_id": "arc-gen", "title": "Gen Arc", "chars": ["Aurora"],
            "summary": "Aurora investigates a cult.", "open_threads": [], "scenes": [],
        }),
        patch("app.calliope_shell.plot_arc.append_scene", return_value={"scene_order": 0}),
    ):
        sys.argv = [
            "generate_scene.py",
            "--prompt", "Aurora investigates the vault",
            "--scene-type", "mystery_investigation",
            "--arc", "arc-gen",
            "--output", str(output_file),
        ]
        with pytest.raises(SystemExit) as exc:
            gs.main()
        assert exc.value.code == 0
    assert mock_dispatch.called
    # Verify arc context was in prompt
    call_prompt = mock_dispatch.call_args[0][1]
    assert "Arc context" in call_prompt or "Gen Arc" in call_prompt


# TPA10 — backwards-compat: --arc absent → atomic scene (no regression)
def test_tpa10_no_arc_backwards_compat(tmp_path):
    import generate_scene as gs  # noqa: PLC0415

    output_file = tmp_path / "atomic_scene.md"
    with (
        patch.object(gs, "dispatch_to_tier", return_value="Clean atomic scene."),
        patch.object(gs, "route_scene", return_value={"tier": "cerebras_workhorse", "provider": "cerebras"}),
        patch.object(gs, "load_config", return_value={}),
        patch.object(gs, "_publish_emotion"),
    ):
        sys.argv = [
            "generate_scene.py",
            "--prompt", "Simple prompt no arc",
            "--output", str(output_file),
        ]
        with pytest.raises(SystemExit) as exc:
            gs.main()
        assert exc.value.code == 0
    content = output_file.read_text(encoding="utf-8")
    assert "Clean atomic scene." in content
    assert "Arc context:" not in content
