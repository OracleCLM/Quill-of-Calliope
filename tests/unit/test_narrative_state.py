"""Unit test per scripts/narrative_state.py.

Copre:
  - CharState / PlotThread defaults e attributi
  - NarrativeState serialization (to_dict / from_dict)
  - save() / load() file I/O con tmp_path
  - to_prompt_context() formato stringa
  - _extract_json() static (fence markdown + raw JSON)
  - update_from_scene() con dispatch_fn mock (no HTTP)
"""
from __future__ import annotations

import json

from scripts.narrative_state import CharState, NarrativeState, PlotThread


# ── CharState defaults ────────────────────────────────────────────────────────

def test_char_state_defaults():
    cs = CharState(name="Aurora")
    assert cs.emotion == "neutral"
    assert cs.status == "alive"
    assert cs.location == ""


# ── PlotThread defaults ───────────────────────────────────────────────────────

def test_plot_thread_defaults():
    pt = PlotThread(name="Il tradimento", description="Aurora tradisce il re")
    assert pt.status == "active"
    assert pt.scenes_mentioned == []


# ── to_dict / from_dict roundtrip ─────────────────────────────────────────────

def test_roundtrip_empty():
    ns = NarrativeState()
    restored = NarrativeState.from_dict(ns.to_dict())
    assert restored.chars == {}
    assert restored.plot_threads == []
    assert restored.current_location == ns.current_location


def test_roundtrip_with_char():
    ns = NarrativeState()
    ns.chars["Aurora"] = CharState(name="Aurora", emotion="determined", status="wounded")
    d = ns.to_dict()
    restored = NarrativeState.from_dict(d)
    assert restored.chars["Aurora"].emotion == "determined"
    assert restored.chars["Aurora"].status == "wounded"


def test_roundtrip_with_plot_thread():
    ns = NarrativeState()
    ns.plot_threads.append(PlotThread(
        name="Oscurità del nord", description="Il drago avanza",
        scenes_mentioned=["1", "3"],
    ))
    restored = NarrativeState.from_dict(ns.to_dict())
    assert restored.plot_threads[0].name == "Oscurità del nord"
    assert "1" in restored.plot_threads[0].scenes_mentioned


# ── save / load ───────────────────────────────────────────────────────────────

def test_save_and_load(tmp_path):
    ns = NarrativeState(current_location="Village of Mist", scene_count=7)
    ns.chars["Kira"] = CharState(name="Kira", emotion="sad")
    path = tmp_path / "state.json"
    ns.save(path)
    loaded = NarrativeState.load(path)
    assert loaded.current_location == "Village of Mist"
    assert loaded.scene_count == 7
    assert loaded.chars["Kira"].emotion == "sad"


def test_load_nonexistent_returns_fresh(tmp_path):
    ns = NarrativeState.load(tmp_path / "no_such_file.json")
    assert ns.chars == {}
    assert ns.scene_count == 0


def test_load_corrupt_returns_fresh(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{{{ not json", encoding="utf-8")
    ns = NarrativeState.load(p)
    assert ns.chars == {}


# ── to_prompt_context ────────────────────────────────────────────────────────

def test_prompt_context_contains_location():
    ns = NarrativeState(current_location="Temple of Dawn")
    ctx = ns.to_prompt_context()
    assert "Temple of Dawn" in ctx


def test_prompt_context_char_traits():
    ns = NarrativeState()
    ns.chars["Kira"] = CharState(name="Kira", status="wounded", emotion="fearful")
    ctx = ns.to_prompt_context()
    assert "Kira" in ctx
    assert "wounded" in ctx


def test_prompt_context_active_threads():
    ns = NarrativeState()
    ns.plot_threads.append(PlotThread(name="Il velo oscuro", description="...", status="active"))
    ns.plot_threads.append(PlotThread(name="Closed arc", description="...", status="resolved"))
    ctx = ns.to_prompt_context()
    assert "Il velo oscuro" in ctx
    assert "Closed arc" not in ctx


# ── _extract_json ─────────────────────────────────────────────────────────────

def test_extract_json_raw():
    raw = '{"key": "value"}'
    assert json.loads(NarrativeState._extract_json(raw)) == {"key": "value"}


def test_extract_json_fenced():
    raw = "Qui ho il risultato:\n```json\n{\"ok\": true}\n```\nAltro testo."
    assert json.loads(NarrativeState._extract_json(raw)) == {"ok": True}


def test_extract_json_with_noise():
    raw = "Risposta: {\"x\": 42} fine."
    extracted = NarrativeState._extract_json(raw)
    assert json.loads(extracted)["x"] == 42


# ── update_from_scene con mock dispatch ───────────────────────────────────────

_MOCK_RESPONSE = json.dumps({
    "chars_seen": [
        {"name": "Aurora", "emotion": "determined", "location": "Castle Gate", "status": "alive"}
    ],
    "location": "Castle Gate",
    "time": "dusk",
    "plot_threads": [
        {"name": "Siege", "description": "L'assedio comincia", "status": "active"}
    ],
})


def test_update_from_scene_chars_updated():
    ns = NarrativeState()
    delta = ns.update_from_scene(
        "Aurora stood at the Castle Gate at dusk.",
        scene_type="action_combat",
        scene_num=1,
        dispatch_fn=lambda _: _MOCK_RESPONSE,
    )
    assert "Aurora" in ns.chars
    assert ns.chars["Aurora"].emotion == "determined"
    assert "Aurora" in delta["chars_updated"]


def test_update_from_scene_location_changed():
    ns = NarrativeState(current_location="Unknown")
    ns.update_from_scene(
        "text", "action_combat", 1,
        dispatch_fn=lambda _: _MOCK_RESPONSE,
    )
    assert ns.current_location == "Castle Gate"


def test_update_from_scene_plot_thread_added():
    ns = NarrativeState()
    ns.update_from_scene(
        "text", "action_combat", 1,
        dispatch_fn=lambda _: _MOCK_RESPONSE,
    )
    assert any(pt.name == "Siege" for pt in ns.plot_threads)


def test_update_from_scene_dispatch_error_graceful():
    ns = NarrativeState()
    def bad_dispatch(_): raise RuntimeError("gateway down")
    delta = ns.update_from_scene("text", "action_combat", 1, dispatch_fn=bad_dispatch)
    assert delta["chars_updated"] == []
    assert ns.scene_count == 1  # incrementato prima del dispatch


def test_update_from_scene_invalid_emotion_defaults():
    resp = json.dumps({
        "chars_seen": [{"name": "Kira", "emotion": "FLYING", "location": "", "status": "alive"}],
        "location": "", "time": "", "plot_threads": [],
    })
    ns = NarrativeState()
    ns.update_from_scene("text", "ooc_meta", 1, dispatch_fn=lambda _: resp)
    assert ns.chars["Kira"].emotion == "neutral"
