"""GAP-59: test per summarizer — default_summarizer, summarize_range,
compress_history, apply_ghosting."""

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


# ── helpers ───────────────────────────────────────────────────────────────────


def _msg(author: str, content: str, ghost: bool = False) -> SceneMessage:
    return SceneMessage(author=author, content=content, ghost=ghost)


def _scene(*messages: SceneMessage) -> SceneChat:
    s = SceneChat(id="sc", name="Test")
    s.messages = list(messages)
    return s


# ── default_summarizer ────────────────────────────────────────────────────────


def test_default_summarizer_returns_string():
    assert isinstance(default_summarizer("Hello world."), str)


def test_default_summarizer_starts_with_prefix():
    result = default_summarizer("Hello world.")
    assert result.startswith("Summary: ")


def test_default_summarizer_includes_short_text():
    result = default_summarizer("The hero runs.")
    assert "hero" in result


def test_default_summarizer_takes_first_two_sentences():
    text = "First sentence. Second sentence. Third sentence."
    result = default_summarizer(text)
    assert "First" in result
    assert "Second" in result


def test_default_summarizer_long_text_truncated():
    long_text = "This is a long sentence that repeats. " * 20
    result = default_summarizer(long_text)
    assert len(result) <= 205  # "Summary: " (9) + 200 chars + small tolerance for "..."


def test_default_summarizer_empty_string():
    result = default_summarizer("")
    assert isinstance(result, str)
    assert result.startswith("Summary: ")


def test_default_summarizer_deterministic():
    text = "Aurora attacks. Mao defends."
    assert default_summarizer(text) == default_summarizer(text)


# ── summarize_range ───────────────────────────────────────────────────────────


def test_summarize_range_empty_returns_empty():
    assert summarize_range([]) == ""


def test_summarize_range_single_message_includes_author():
    msgs = [_msg("Aurora", "I attack the dragon.")]
    result = summarize_range(msgs)
    assert "Aurora" in result


def test_summarize_range_single_message_includes_content():
    msgs = [_msg("Aurora", "I attack the dragon.")]
    result = summarize_range(msgs)
    assert "dragon" in result


def test_summarize_range_multiple_messages_joins():
    msgs = [_msg("Aurora", "First line."), _msg("Mao", "Second line.")]
    result = summarize_range(msgs)
    assert "Aurora" in result or "Mao" in result


def test_summarize_range_uses_custom_fn():
    def custom(text: str) -> str:
        return "CUSTOM"
    msgs = [_msg("A", "any content")]
    assert summarize_range(msgs, summarizer_fn=custom) == "CUSTOM"


def test_summarize_range_uses_default_fn_when_none():
    msgs = [_msg("A", "content here.")]
    result = summarize_range(msgs, summarizer_fn=None)
    assert result.startswith("Summary: ")


# ── compress_history ──────────────────────────────────────────────────────────


def test_compress_history_returns_compression_result():
    s = _scene()
    result = compress_history(s)
    assert isinstance(result, CompressionResult)


def test_compress_history_empty_scene():
    s = _scene()
    result = compress_history(s)
    assert result.kept == []
    assert result.summaries == []
    assert result.ghosted_count == 0


def test_compress_history_few_msgs_all_kept():
    s = _scene(_msg("A", "m1"), _msg("B", "m2"), _msg("C", "m3"))
    result = compress_history(s, keep_recent_n=6)
    assert len(result.kept) == 3
    assert result.summaries == []
    assert result.ghosted_count == 0


def test_compress_history_kept_is_last_n():
    msgs = [_msg("A", f"msg {i}") for i in range(10)]
    s = _scene(*msgs)
    result = compress_history(s, keep_recent_n=4)
    assert len(result.kept) == 4
    assert result.kept[0].content == "msg 6"
    assert result.kept[-1].content == "msg 9"


def test_compress_history_ghosted_count():
    msgs = [_msg("A", f"m{i}") for i in range(10)]
    s = _scene(*msgs)
    result = compress_history(s, keep_recent_n=4)
    assert result.ghosted_count == 6


def test_compress_history_summaries_generated():
    msgs = [_msg("A", f"msg {i}.") for i in range(10)]
    s = _scene(*msgs)
    result = compress_history(s, keep_recent_n=4, range_size=3)
    assert len(result.summaries) > 0


def test_compress_history_does_not_mutate_scene():
    msgs = [_msg("A", f"m{i}") for i in range(8)]
    s = _scene(*msgs)
    original_count = len(s.messages)
    compress_history(s, keep_recent_n=3)
    assert len(s.messages) == original_count


def test_compress_history_ghost_messages_excluded():
    msgs = [_msg("A", "visible"), _msg("B", "ghost_msg", ghost=True)]
    s = _scene(*msgs)
    result = compress_history(s, keep_recent_n=10)
    assert all(not m.ghost for m in result.kept)


# ── apply_ghosting ────────────────────────────────────────────────────────────


def test_apply_ghosting_returns_scene_chat():
    s = _scene(_msg("A", "hello"))
    result = apply_ghosting(s)
    assert isinstance(result, SceneChat)


def test_apply_ghosting_does_not_mutate_original():
    msgs = [_msg("A", f"m{i}") for i in range(5)]
    s = _scene(*msgs)
    apply_ghosting(s, keep_recent_n=2)
    assert all(not m.ghost for m in s.messages)


def test_apply_ghosting_older_messages_marked():
    msgs = [_msg("A", f"m{i}") for i in range(5)]
    s = _scene(*msgs)
    result = apply_ghosting(s, keep_recent_n=2)
    assert result.messages[0].ghost is True
    assert result.messages[1].ghost is True
    assert result.messages[2].ghost is True


def test_apply_ghosting_recent_messages_not_ghosted():
    msgs = [_msg("A", f"m{i}") for i in range(5)]
    s = _scene(*msgs)
    result = apply_ghosting(s, keep_recent_n=2)
    assert result.messages[3].ghost is False
    assert result.messages[4].ghost is False


def test_apply_ghosting_keep_zero_all_ghost():
    msgs = [_msg("A", f"m{i}") for i in range(4)]
    s = _scene(*msgs)
    result = apply_ghosting(s, keep_recent_n=0)
    assert all(m.ghost for m in result.messages)


def test_apply_ghosting_keep_exceeds_total_none_ghost():
    msgs = [_msg("A", f"m{i}") for i in range(3)]
    s = _scene(*msgs)
    result = apply_ghosting(s, keep_recent_n=10)
    assert all(not m.ghost for m in result.messages)


def test_apply_ghosting_empty_scene():
    s = _scene()
    result = apply_ghosting(s, keep_recent_n=3)
    assert result.messages == []
