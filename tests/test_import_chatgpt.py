"""Sprint F3 — import_chatgpt_history test suite."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from import_chatgpt_history import parse_conversations, _is_rp_related, _categorize


def _make_conv(title="RP Session", role="user", text="Aurora drew her sword in the moonlight."):
    return [{
        "id": "conv_001",
        "title": title,
        "create_time": 1700000000,
        "mapping": {
            "node_1": {
                "message": {
                    "author": {"role": role},
                    "content": {"parts": [text]},
                    "create_time": 1700000100,
                }
            }
        },
    }]


def test_fc1_parse_basic():
    records = parse_conversations(_make_conv())
    assert len(records) == 1
    assert records[0]["source"] == "chatgpt"
    assert records[0]["role"] == "user"
    assert "Aurora" in records[0]["text"]


def test_fc2_rp_detection():
    assert _is_rp_related("Write as Aurora in this fantasy scene")
    assert _is_rp_related("Let's do some roleplay")
    assert not _is_rp_related("What is the capital of France?")


def test_fc3_categorize():
    assert _categorize("Please translate this to Italian") == "translation"
    assert _categorize("Write a scene where Aurora enters") == "drafting"
    assert _categorize("What if we add a new magic system?") == "brainstorming"
    assert _categorize("Tell me about the faction history") == "lore"
    assert _categorize("What time is it?") == "general"


def test_fc4_rp_only_filter():
    data = [{
        "id": "c1", "title": "Mixed", "create_time": 0,
        "mapping": {
            "n1": {"message": {"author": {"role": "user"}, "content": {"parts": ["Aurora cast a yokai spell"]}, "create_time": 0}},
            "n2": {"message": {"author": {"role": "user"}, "content": {"parts": ["What is 2+2? Just math."]}, "create_time": 0}},
        },
    }]
    all_records = parse_conversations(data, rp_only=False)
    rp_records = parse_conversations(data, rp_only=True)
    assert len(all_records) == 2
    assert len(rp_records) == 1
    assert "yokai" in rp_records[0]["text"].lower()


def test_fc5_skips_system_messages():
    data = [{
        "id": "c1", "title": "T", "create_time": 0,
        "mapping": {
            "n1": {"message": {"author": {"role": "system"}, "content": {"parts": ["You are helpful"]}, "create_time": 0}},
            "n2": {"message": {"author": {"role": "user"}, "content": {"parts": ["Aurora the yokai queen speaks"]}, "create_time": 0}},
        },
    }]
    records = parse_conversations(data)
    assert len(records) == 1
    assert records[0]["role"] == "user"


def test_fc6_main_writes_jsonl(tmp_path):
    conv_file = tmp_path / "conversations.json"
    conv_file.write_text(json.dumps(_make_conv()), encoding="utf-8")
    output = tmp_path / "out.jsonl"

    from import_chatgpt_history import main
    rc = main(["--input", str(conv_file), "--output", str(output)])
    assert rc == 0
    assert output.exists()
    lines = output.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["source"] == "chatgpt"


def test_fc7_empty_text_skipped():
    data = [{
        "id": "c1", "title": "T", "create_time": 0,
        "mapping": {
            "n1": {"message": {"author": {"role": "user"}, "content": {"parts": [""]}, "create_time": 0}},
            "n2": {"message": {"author": {"role": "user"}, "content": {"parts": ["short"]}, "create_time": 0}},
        },
    }]
    records = parse_conversations(data)
    assert len(records) == 0
