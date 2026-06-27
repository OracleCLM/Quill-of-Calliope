"""GAP-53: test per detect_open_threads — regex heuristics su scene summaries."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

import app.calliope_shell.plot_arc as pa


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path):
    db = tmp_path / "arc_threads.db"
    monkeypatch.setattr(pa, "DB_PATH", db)
    monkeypatch.setattr("app.calliope_shell.plot_arc.audit_trail", MagicMock(), raising=False)
    pa.init_db()
    yield


def _arc_with_scenes(arc_id: str, summaries: list[str]) -> None:
    pa.create_arc(arc_id, "Arco test", [])
    with pa._lock, pa._conn() as c:
        for i, summary in enumerate(summaries):
            c.execute(
                "INSERT INTO plot_arc_scenes"
                "(arc_id, scene_order, scene_id, scene_md_path, scene_summary) "
                "VALUES(?,?,?,?,?)",
                (arc_id, i, f"{arc_id}_s{i}", "/fake/path.md", summary),
            )


# ── arc senza scene ───────────────────────────────────────────────────────────


def test_detect_no_arc_returns_empty():
    result = pa.detect_open_threads("inesistente")
    assert result == []


def test_detect_arc_no_scenes_returns_empty():
    pa.create_arc("empty-arc", "T", [])
    result = pa.detect_open_threads("empty-arc")
    assert result == []


# ── estrazione nomi (tipo 'character') ────────────────────────────────────────


def test_detect_extracts_capitalized_name():
    _arc_with_scenes("char-arc", ["Aurora was searching for the ancient scroll."])
    threads = pa.detect_open_threads("char-arc")
    char_threads = [t for t in threads if t["type"] == "character"]
    names = [t["thread"] for t in char_threads]
    assert any("Aurora" in n for n in names)


def test_detect_skips_stop_words():
    # Stop words come parole singole isolate: non devono generare char threads
    _arc_with_scenes("skip-arc", ["They ran. She hid. The group scattered."])
    threads = pa.detect_open_threads("skip-arc")
    char_names = [t["thread"] for t in threads if t["type"] == "character"]
    # I thread di tipo character non devono contenere stop words come nomi soli
    for stop in ("Character: The", "Character: She", "Character: Her",
                 "Character: They", "Character: Their"):
        assert stop not in char_names


def test_detect_no_duplicate_names_across_scenes():
    _arc_with_scenes("dedup-arc", [
        "Aurora searched for the missing key.",
        "Aurora found the hidden clue.",
    ])
    threads = pa.detect_open_threads("dedup-arc")
    char_threads = [t for t in threads if t["type"] == "character" and "Aurora" in t["thread"]]
    assert len(char_threads) == 1


def test_detect_two_names_in_same_scene():
    _arc_with_scenes("two-arc", ["Aurora and Fiora found a clue."])
    threads = pa.detect_open_threads("two-arc")
    char_names = [t["thread"] for t in threads if t["type"] == "character"]
    assert len(char_names) >= 2


# ── estrazione eventi (tipo 'event') ──────────────────────────────────────────


def test_detect_event_missing_keyword():
    _arc_with_scenes("ev-arc", ["The artifact was missing from the vault."])
    threads = pa.detect_open_threads("ev-arc")
    event_threads = [t for t in threads if t["type"] == "event"]
    assert len(event_threads) >= 1


def test_detect_event_quest_keyword():
    _arc_with_scenes("quest-arc", ["The group accepted the quest."])
    threads = pa.detect_open_threads("quest-arc")
    event_threads = [t for t in threads if t["type"] == "event"]
    assert any("quest" in t["thread"].lower() for t in event_threads)


def test_detect_event_secret_keyword():
    _arc_with_scenes("secret-arc", ["They kept the secret hidden."])
    threads = pa.detect_open_threads("secret-arc")
    event_threads = [t for t in threads if t["type"] == "event"]
    assert any("secret" in t["thread"].lower() for t in event_threads)


def test_detect_case_insensitive_events():
    _arc_with_scenes("ci-arc", ["She ESCAPED from the dungeon."])
    threads = pa.detect_open_threads("ci-arc")
    event_threads = [t for t in threads if t["type"] == "event"]
    assert len(event_threads) >= 1


def test_detect_no_keywords_returns_no_events():
    _arc_with_scenes("noev-arc", ["They walked through the peaceful village."])
    threads = pa.detect_open_threads("noev-arc")
    event_threads = [t for t in threads if t["type"] == "event"]
    assert event_threads == []


# ── struttura risposta ────────────────────────────────────────────────────────


def test_detect_thread_has_required_fields():
    _arc_with_scenes("fields-arc", ["Aurora was searching for the artifact."])
    threads = pa.detect_open_threads("fields-arc")
    assert len(threads) >= 1
    for t in threads:
        assert "thread" in t
        assert "last_scene_idx" in t
        assert "type" in t


def test_detect_last_scene_idx_correct():
    _arc_with_scenes("idx-arc", [
        "First scene with no keywords.",
        "Aurora disappeared into the forest.",
    ])
    threads = pa.detect_open_threads("idx-arc")
    char_threads = [t for t in threads if t["type"] == "character" and "Aurora" in t["thread"]]
    assert len(char_threads) == 1
    assert char_threads[0]["last_scene_idx"] == 1


def test_detect_saves_threads_to_arc(tmp_path):
    _arc_with_scenes("save-arc", ["Aurora was missing."])
    pa.detect_open_threads("save-arc")
    arc = pa.get_arc("save-arc")
    assert isinstance(arc["open_threads"], list)
    assert len(arc["open_threads"]) >= 1
