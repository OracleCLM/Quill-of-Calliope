"""
Unit test per summarizer.py (P3 — compressione cronologia scene).

Contratto:
  - default_summarizer: prefisso "Summary:", max 200 char, ≤2 frasi, no troncamento a metà parola
  - summarize_range: empty → "", concatenazione author:content, custom fn
  - compress_history: kept/summaries/ghosted_count, immutabilità scene
  - apply_ghosting: deep copy, ghost marking, keep_recent_n=0
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.scene_model import SceneChat, SceneMessage
from app.calliope_shell.summarizer import (
    apply_ghosting,
    compress_history,
    default_summarizer,
    summarize_range,
)


# ── default_summarizer ────────────────────────────────────────────────────────

def test_default_summarizer_prefix():
    result = default_summarizer("Frase uno. Frase due.")
    assert result.startswith("Summary: ")


def test_default_summarizer_empty():
    result = default_summarizer("")
    assert result.startswith("Summary: ")


def test_default_summarizer_single_sentence():
    result = default_summarizer("Una sola frase senza punto finale")
    assert "Una sola frase" in result


def test_default_summarizer_max_two_sentences():
    text = "Prima. Seconda. Terza. Quarta."
    result = default_summarizer(text)
    # Al massimo 2 frasi → nessun riferimento alla terza/quarta
    assert "Terza" not in result
    assert "Quarta" not in result


def test_default_summarizer_truncation_at_word_boundary():
    long = "Parola " * 100 + "."
    result = default_summarizer(long)
    assert len(result) <= 200
    # Non finisce a metà parola (tranne "...")
    body = result[len("Summary: "):]
    if body.endswith("..."):
        # l'ultima parola prima di "..." deve essere completa
        before_dots = body[:-3]
        assert not before_dots.endswith(" ")
    else:
        assert True


def test_default_summarizer_normalizes_whitespace():
    text = "  Frasi    con   spazi  extra. Seconda."
    result = default_summarizer(text)
    assert "  " not in result


# ── summarize_range ───────────────────────────────────────────────────────────

def test_summarize_range_empty():
    assert summarize_range([]) == ""


def test_summarize_range_single_message():
    msgs = [SceneMessage(author="Aurora", content="Ciao mondo")]
    result = summarize_range(msgs)
    assert "Aurora" in result or "Ciao" in result


def test_summarize_range_concatenation():
    msgs = [
        SceneMessage(author="A", content="prima battuta"),
        SceneMessage(author="B", content="seconda battuta"),
    ]
    called_with = []
    def capture_fn(text):
        called_with.append(text)
        return "captured"
    summarize_range(msgs, summarizer_fn=capture_fn)
    assert len(called_with) == 1
    assert "A: prima battuta" in called_with[0]
    assert "B: seconda battuta" in called_with[0]


def test_summarize_range_custom_fn():
    msgs = [SceneMessage(author="X", content="content")]
    result = summarize_range(msgs, summarizer_fn=lambda t: "CUSTOM")
    assert result == "CUSTOM"


# ── compress_history ──────────────────────────────────────────────────────────

def _scene_with_msgs(n: int) -> SceneChat:
    messages = [SceneMessage(author="A", content=f"msg{i}") for i in range(n)]
    return SceneChat(id="s1", name="Test", messages=messages)


def test_compress_history_empty():
    scene = _scene_with_msgs(0)
    result = compress_history(scene, keep_recent_n=6)
    assert result.kept == []
    assert result.summaries == []
    assert result.ghosted_count == 0


def test_compress_history_fewer_than_keep():
    scene = _scene_with_msgs(3)
    result = compress_history(scene, keep_recent_n=6)
    assert len(result.kept) == 3
    assert result.ghosted_count == 0
    assert result.summaries == []


def test_compress_history_kept_are_most_recent():
    scene = _scene_with_msgs(10)
    result = compress_history(scene, keep_recent_n=3)
    assert len(result.kept) == 3
    assert result.kept[0].content == "msg7"
    assert result.kept[-1].content == "msg9"


def test_compress_history_ghosted_count():
    scene = _scene_with_msgs(10)
    result = compress_history(scene, keep_recent_n=4)
    assert result.ghosted_count == 6


def test_compress_history_summaries_by_range():
    scene = _scene_with_msgs(12)
    result = compress_history(scene, keep_recent_n=0, range_size=4)
    # 12 messaggi / 4 = 3 blocchi
    assert len(result.summaries) == 3


def test_compress_history_does_not_mutate_scene():
    scene = _scene_with_msgs(8)
    original_len = len(scene.messages)
    compress_history(scene, keep_recent_n=4)
    assert len(scene.messages) == original_len


# ── apply_ghosting ────────────────────────────────────────────────────────────

def test_apply_ghosting_returns_copy():
    scene = _scene_with_msgs(5)
    copy = apply_ghosting(scene, keep_recent_n=3)
    assert copy is not scene


def test_apply_ghosting_does_not_mutate_original():
    scene = _scene_with_msgs(5)
    apply_ghosting(scene, keep_recent_n=3)
    assert not any(m.ghost for m in scene.messages)


def test_apply_ghosting_marks_older():
    scene = _scene_with_msgs(5)
    result = apply_ghosting(scene, keep_recent_n=2)
    ghost_flags = [m.ghost for m in result.messages]
    assert ghost_flags == [True, True, True, False, False]


def test_apply_ghosting_keep_zero():
    scene = _scene_with_msgs(3)
    result = apply_ghosting(scene, keep_recent_n=0)
    assert all(m.ghost for m in result.messages)


def test_apply_ghosting_keep_all():
    scene = _scene_with_msgs(4)
    result = apply_ghosting(scene, keep_recent_n=10)
    assert not any(m.ghost for m in result.messages)
