import pytest
from datetime import datetime, timedelta
from collections import Counter


@pytest.fixture
def sample_ic_messages():
    """Fixture: 10 IC messages with player='Horo', 3 different characters."""
    messages = []
    characters = ["char_A"] * 4 + ["char_B"] * 3 + ["char_C"] * 3
    base_time = datetime(2023, 1, 1, 12, 0)
    for i, char in enumerate(characters):
        messages.append(
            {
                "player": "Horo",
                "character": char,
                "message": f"Message {i} from {char}",
                "type": "IC",
                "scene_id": "scene_0000",  # all within same scene
                "row_idx": i,
                "timestamp": base_time + timedelta(minutes=i * 2),
            }
        )
    return messages


def test_top_chars_extraction(sample_ic_messages):
    """Top-2 chars by IC message count for Horo should include char_A (4 msgs)."""
    char_counter: Counter = Counter()
    for m in sample_ic_messages:
        if m["player"] == "Horo" and m["type"] == "IC" and m["message"] is not None and m["character"] is not None:
            char_counter[m["character"]] += 1

    top_chars = [char for char, _ in char_counter.most_common(2)]

    assert len(top_chars) == 2
    assert "char_A" in top_chars  # 4 messages — always first
    assert any(c in top_chars for c in ["char_B", "char_C"])  # either of the 3-message chars


def test_context_window(sample_ic_messages):
    """Target message at row_idx=4 should find 3 previous IC messages in same scene."""
    target = sample_ic_messages[4]  # row_idx=4, scene_0000
    K = 3

    candidates = [
        m
        for m in sample_ic_messages
        if (
            m["type"] == "IC"
            and m["message"] is not None
            and m["scene_id"] == target["scene_id"]
            and m["row_idx"] < target["row_idx"]
        )
    ]
    candidates.sort(key=lambda x: x["row_idx"])
    context_prev_msgs = candidates[-K:]

    assert len(context_prev_msgs) == 3


def test_chatml_format():
    """ChatML record must have exactly 3 messages: system, user, assistant."""
    char_name = "Aurora"
    char_message = "The stars align at dusk."
    context_prev = [
        {"char": "NARRATOR", "player": "Horo", "text": "A howl echoes in the distance."},
        {"char": "Pdor", "player": "OtherPlayer", "text": "What was that?"},
        {"char": "Aurora", "player": "Horo", "text": "Nothing to worry about."},
    ]

    context_str = "\n".join(f"[{m['char'] or m['player']}]: {m['text']}" for m in context_prev)

    chatml_record = {
        "messages": [
            {"role": "system", "content": f"Roleplay as {char_name}."},
            {"role": "user", "content": context_str},
            {"role": "assistant", "content": char_message},
        ]
    }

    msgs = chatml_record["messages"]
    assert len(msgs) == 3
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert msgs[2]["role"] == "assistant"
    assert msgs[0]["content"].startswith("Roleplay as")
    assert msgs[2]["content"] == char_message
