"""Tests for NarrativeState cross-scene tracking."""
from __future__ import annotations

import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from narrative_state import CharState, NarrativeState, PlotThread  # noqa: E402


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_state() -> NarrativeState:
    s = NarrativeState(current_location="palace gardens", current_time="dusk")
    s.chars["Aurora"] = CharState("Aurora", emotion="determined", status="alive",
                                   location="palace gardens")
    s.chars["Filomena"] = CharState("Filomena", emotion="neutral", status="alive",
                                     location="palace gardens")
    s.plot_threads.append(PlotThread("assassin arc", "Aurora hunts the assassin", "active",
                                      ["1"], "scene_1"))
    return s


def _analysis_json(chars=None, location="throne room", time="evening",
                   threads=None) -> str:
    chars = chars or [{"name": "Aurora", "emotion": "wounded", "location": "throne room", "status": "wounded"}]
    threads = threads or [{"name": "assassin arc", "description": "Assassin escaped", "status": "active"}]
    return json.dumps({"chars_seen": chars, "location": location, "time": time,
                       "plot_threads": threads})


# ── Test 1: save/load round-trip ─────────────────────────────────────────────

class TestSaveLoad:
    def test_round_trip(self, tmp_path):
        s = _make_state()
        path = tmp_path / "state.json"
        s.save(path)
        loaded = NarrativeState.load(path)
        assert loaded.current_location == "palace gardens"
        assert loaded.current_time == "dusk"
        assert "Aurora" in loaded.chars
        assert loaded.chars["Aurora"].emotion == "determined"
        assert len(loaded.plot_threads) == 1
        assert loaded.plot_threads[0].name == "assassin arc"

    def test_load_missing_returns_default(self, tmp_path):
        s = NarrativeState.load(tmp_path / "nonexistent.json")
        assert s.scene_count == 0
        assert s.chars == {}

    def test_save_atomic(self, tmp_path):
        s = _make_state()
        path = tmp_path / "state.json"
        s.save(path)
        assert path.exists()
        assert not path.with_suffix(".json.tmp").exists()


# ── Test 2: update_from_scene mock LLM ──────────────────────────────────────

class TestUpdateFromScene:
    def test_char_emotion_updated(self):
        s = _make_state()
        def mock_fn(_): return _analysis_json()
        delta = s.update_from_scene("Aurora was wounded in the fight.", "action_combat",
                                     scene_num=2, dispatch_fn=mock_fn)
        assert "Aurora" in delta["chars_updated"]
        assert s.chars["Aurora"].emotion == "wounded"
        assert s.chars["Aurora"].status == "wounded"

    def test_location_updated(self):
        s = _make_state()
        def mock_fn(_): return _analysis_json()
        delta = s.update_from_scene("They moved to the throne room.", "intimate_dialogue",
                                     scene_num=2, dispatch_fn=mock_fn)
        assert delta["location_changed"] is True
        assert s.current_location == "throne room"

    def test_scene_count_incremented(self):
        s = _make_state()
        s.scene_count = 3
        def mock_fn(_): return _analysis_json()
        s.update_from_scene("text", "action_combat", scene_num=4, dispatch_fn=mock_fn)
        assert s.scene_count == 4

    def test_graceful_on_bad_json(self):
        s = _make_state()
        def mock_fn(_): return "not json at all"
        s.update_from_scene("some text", "action_combat", 2, dispatch_fn=mock_fn)
        # Should not crash; scene_count still incremented
        assert s.scene_count == 1


# ── Test 3: plot thread lifecycle ────────────────────────────────────────────

class TestPlotThreads:
    def test_thread_resolved(self):
        s = _make_state()
        resolved_json = _analysis_json(threads=[
            {"name": "assassin arc", "description": "Assassin caught!", "status": "resolved"}
        ])
        def mock_fn(_): return resolved_json
        delta = s.update_from_scene("The assassin was caught.", "action_aftermath",
                                     scene_num=2, dispatch_fn=mock_fn)
        assert "assassin arc" in delta["threads_updated"]
        assert s.plot_threads[0].status == "resolved"

    def test_new_thread_added(self):
        s = _make_state()
        new_thread_json = _analysis_json(threads=[
            {"name": "assassin arc", "description": "ongoing", "status": "active"},
            {"name": "palace betrayal", "description": "Guard betrayed the queen", "status": "active"},
        ])
        def mock_fn(_): return new_thread_json
        s.update_from_scene("A guard was the traitor.", "mystery_investigation",
                             scene_num=2, dispatch_fn=mock_fn)
        names = [pt.name for pt in s.plot_threads]
        assert "palace betrayal" in names


# ── Test 4: location transition tracking ─────────────────────────────────────

class TestLocationTracking:
    def test_location_transitions_logged(self):
        s = _make_state()
        assert s.current_location == "palace gardens"
        def mock_fn(_): return _analysis_json(location="throne room")
        s.update_from_scene("They entered the throne room.", "intimate_dialogue",
                             scene_num=2, dispatch_fn=mock_fn)
        assert s.current_location == "throne room"

    def test_unchanged_location_no_delta(self):
        s = _make_state()
        same_loc_json = _analysis_json(location="palace gardens")
        def mock_fn(_): return same_loc_json
        delta = s.update_from_scene("Still in the gardens.", "lore_exposition",
                                     scene_num=2, dispatch_fn=mock_fn)
        assert delta["location_changed"] is False


# ── Test 5: cross-scene char state persistence ───────────────────────────────

class TestCharPersistence:
    def test_wounded_status_persists(self, tmp_path):
        s = _make_state()
        path = tmp_path / "state.json"

        # Scene 2: Aurora gets wounded
        _resp = _analysis_json(chars=[{"name": "Aurora", "emotion": "determined",
                                        "location": "throne room", "status": "wounded"}])
        def mock_fn(_): return _resp
        s.update_from_scene("Aurora was struck.", "action_combat", 2, dispatch_fn=mock_fn)
        s.save(path)

        # Reload and check
        s2 = NarrativeState.load(path)
        assert s2.chars["Aurora"].status == "wounded"
        assert s2.current_location == "throne room"

    def test_prompt_context_reflects_wounded(self):
        s = _make_state()
        s.chars["Aurora"].status = "wounded"
        ctx = s.to_prompt_context()
        assert "wounded" in ctx
        assert "Aurora" in ctx
        assert "assassin arc" in ctx
