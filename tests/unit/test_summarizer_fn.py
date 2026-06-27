"""GAP-33: test unitari per summarizer — default_summarizer, compress_history, apply_ghosting."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.scene_model import SceneChat, SceneMessage
from app.calliope_shell.summarizer import (
    CompressionResult,
    apply_ghosting,
    compress_history,
    default_summarizer,
    summarize_range,
)


def _msg(author, content, ghost=False):
    return SceneMessage(author=author, content=content, ghost=ghost)


def _scene(*msgs):
    return SceneChat(id="test-scene", name="Test", messages=list(msgs))


# --- default_summarizer ------------------------------------------------------


def test_default_summarizer_prefix():
    result = default_summarizer("Aurora arrivò. Tingyun rise.")
    assert result.startswith("Summary:")


def test_default_summarizer_short_text():
    result = default_summarizer("Aurora è arrivata.")
    assert "Aurora" in result


def test_default_summarizer_deterministic():
    text = "La battaglia iniziò. Le spade tintinnarono nel silenzio."
    assert default_summarizer(text) == default_summarizer(text)


def test_default_summarizer_truncates_at_200():
    long_text = "Parola " * 100
    result = default_summarizer(long_text)
    assert len(result) <= 200 + len("Summary: ")


def test_default_summarizer_empty_text():
    result = default_summarizer("")
    assert result.startswith("Summary:")


# --- summarize_range ---------------------------------------------------------


def test_summarize_range_empty_returns_empty():
    assert summarize_range([]) == ""


def test_summarize_range_calls_fn():
    msgs = [_msg("A", "testo"), _msg("B", "altro")]
    result = summarize_range(msgs, summarizer_fn=lambda t: "RIASSUNTO: " + t[:10])
    assert "RIASSUNTO" in result


def test_summarize_range_default_fn_used():
    msgs = [_msg("Aria", "La nebbia si addensava sul castello.")]
    result = summarize_range(msgs)
    assert result.startswith("Summary:")


# --- compress_history --------------------------------------------------------


def test_compress_history_empty_scene():
    cr = compress_history(_scene())
    assert isinstance(cr, CompressionResult)
    assert cr.ghosted_count == 0
    assert cr.kept == []


def test_compress_history_keeps_recent_n():
    scene = _scene(*[_msg(f"C{i}", f"msg{i}") for i in range(10)])
    cr = compress_history(scene, keep_recent_n=4)
    assert len(cr.kept) == 4
    assert cr.kept[-1].content == "msg9"


def test_compress_history_ghosted_count():
    scene = _scene(*[_msg("C", f"msg{i}") for i in range(10)])
    cr = compress_history(scene, keep_recent_n=4)
    assert cr.ghosted_count == 6


def test_compress_history_has_summaries():
    scene = _scene(*[_msg("C", f"msg{i}") for i in range(12)])
    cr = compress_history(scene, keep_recent_n=4, range_size=4)
    assert len(cr.summaries) == 2


def test_compress_history_does_not_mutate_scene():
    msgs = [_msg("C", f"msg{i}") for i in range(8)]
    scene = _scene(*msgs)
    compress_history(scene, keep_recent_n=3)
    assert all(not m.ghost for m in scene.messages)


def test_compress_history_skips_existing_ghosts():
    scene = _scene(
        _msg("C", "ghost", ghost=True),
        *[_msg("C", f"msg{i}") for i in range(8)],
    )
    cr = compress_history(scene, keep_recent_n=4)
    assert cr.ghosted_count == 4


# --- apply_ghosting ----------------------------------------------------------


def test_apply_ghosting_returns_copy():
    scene = _scene(*[_msg("C", f"m{i}") for i in range(6)])
    result = apply_ghosting(scene, keep_recent_n=3)
    assert result is not scene


def test_apply_ghosting_marks_older_as_ghost():
    scene = _scene(*[_msg("C", f"m{i}") for i in range(6)])
    result = apply_ghosting(scene, keep_recent_n=3)
    for i, msg in enumerate(result.messages):
        if i < 3:
            assert msg.ghost is True
        else:
            assert msg.ghost is False


def test_apply_ghosting_keep_all_no_ghost():
    scene = _scene(*[_msg("C", f"m{i}") for i in range(4)])
    result = apply_ghosting(scene, keep_recent_n=10)
    assert all(not m.ghost for m in result.messages)


def test_apply_ghosting_original_unchanged():
    scene = _scene(*[_msg("C", f"m{i}") for i in range(6)])
    apply_ghosting(scene, keep_recent_n=2)
    assert all(not m.ghost for m in scene.messages)
