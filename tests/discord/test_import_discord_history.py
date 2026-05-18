"""Tests for scripts/import_discord_history.py — parse_channel() unit tests."""

from __future__ import annotations

import json

# Import the function under test
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from import_discord_history import parse_channel  # noqa: E402


TUPPER_NAMES = {"Grimm", "Nathan Explosion", "Narrator"}

FIXTURE_CHANNEL: dict = {
    "guild": {"id": "111111111111111111", "name": "Yokai RPG"},
    "channel": {
        "id": "222222222222222222",
        "name": "rp-general",
        "type": "GuildTextChat",
        "topic": "General RP channel",
    },
    "messages": [
        # Message 1: normal IC message, non-bot human player
        {
            "id": "100000000000000001",
            "type": "Default",
            "timestamp": "2024-01-15T20:00:00.000+00:00",
            "timestampEdited": None,
            "content": "Ira looks around the tavern.",
            "author": {
                "id": "600000000000000001",
                "name": "Player1",
                "discriminator": "0000",
                "nickname": "Nic",
                "isBot": False,
                "roles": [],
                "avatarUrl": "",
            },
            "attachments": [],
            "embeds": [],
            "reactions": [],
            "mentions": [],
            "reference": None,
        },
        # Message 2: Tupperbox proxy — isBot=True, name is a known tupper
        {
            "id": "100000000000000002",
            "type": "Default",
            "timestamp": "2024-01-15T20:01:00.000+00:00",
            "timestampEdited": None,
            "content": "Grimm steps out of the shadows, his cloak billowing.",
            "author": {
                "id": "700000000000000001",  # Tupperbox bot user ID
                "name": "Grimm",
                "discriminator": "0000",
                "nickname": None,
                "isBot": True,
                "roles": [],
                "avatarUrl": "",
            },
            "attachments": [],
            "embeds": [],
            "reactions": [{"emoji": {"name": "❤️"}, "count": 2}],
            "mentions": [],
            "reference": None,
        },
        # Message 3: OOC reply with reference
        {
            "id": "100000000000000003",
            "type": "Reply",
            "timestamp": "2024-01-15T20:02:00.000+00:00",
            "timestampEdited": None,
            "content": "(OOC: ciao, tutto ok?)",
            "author": {
                "id": "600000000000000002",
                "name": "Player2",
                "discriminator": "0000",
                "nickname": None,
                "isBot": False,
                "roles": [],
                "avatarUrl": "",
            },
            "attachments": [],
            "embeds": [],
            "reactions": [],
            "mentions": [],
            "reference": {
                "messageId": "100000000000000001",
                "channelId": "222222222222222222",
                "guildId": "111111111111111111",
            },
        },
    ],
    "messageCount": 3,
}


def test_parse_channel_returns_three_records():
    records = parse_channel(FIXTURE_CHANNEL, TUPPER_NAMES)
    assert len(records) == 3


def test_record_0_is_ic():
    records = parse_channel(FIXTURE_CHANNEL, TUPPER_NAMES)
    rec = records[0]
    assert rec["tag"] == "IC"
    assert rec["is_bot"] is False
    assert rec["tupperbox_proxy"] is False
    assert rec["message_id"] == "100000000000000001"
    assert rec["channel_id"] == "222222222222222222"
    assert rec["guild_id"] == "111111111111111111"
    assert rec["reply_to"] is None
    assert rec["author_nick"] == "Nic"


def test_record_1_tupperbox_proxy():
    records = parse_channel(FIXTURE_CHANNEL, TUPPER_NAMES)
    rec = records[1]
    assert rec["tupperbox_proxy"] is True
    assert rec["is_bot"] is True
    assert rec["author_name"] == "Grimm"
    assert rec["tag"] == "IC"  # content starts with "Grimm steps...", not OOC
    assert len(rec["reactions"]) == 1


def test_record_2_is_ooc():
    records = parse_channel(FIXTURE_CHANNEL, TUPPER_NAMES)
    rec = records[2]
    assert rec["tag"] == "OOC"
    assert rec["reply_to"] == "100000000000000001"
    assert rec["is_bot"] is False
    assert rec["tupperbox_proxy"] is False


def test_parent_channel_id_none_for_text_channel():
    records = parse_channel(FIXTURE_CHANNEL, TUPPER_NAMES)
    for rec in records:
        assert rec["parent_channel_id"] is None


def test_parse_channel_thread_sets_parent_id():
    thread_data: dict = {
        "guild": {"id": "111111111111111111", "name": "Yokai RPG"},
        "channel": {
            "id": "333333333333333333",
            "name": "thread-one",
            "type": "GuildPublicThread",
            "categoryId": "222222222222222222",
            "topic": "",
        },
        "messages": [
            {
                "id": "200000000000000001",
                "type": "Default",
                "timestamp": "2024-01-16T10:00:00.000+00:00",
                "timestampEdited": None,
                "content": "A message in a thread.",
                "author": {
                    "id": "600000000000000001",
                    "name": "Player1",
                    "discriminator": "0000",
                    "nickname": None,
                    "isBot": False,
                    "roles": [],
                    "avatarUrl": "",
                },
                "attachments": [],
                "embeds": [],
                "reactions": [],
                "mentions": [],
                "reference": None,
            }
        ],
        "messageCount": 1,
    }
    records = parse_channel(thread_data, TUPPER_NAMES)
    assert len(records) == 1
    assert records[0]["parent_channel_id"] == "222222222222222222"


def test_system_message_tag():
    sys_data: dict = {
        "guild": {"id": "111111111111111111", "name": "Yokai RPG"},
        "channel": {
            "id": "222222222222222222",
            "name": "rp-general",
            "type": "GuildTextChat",
        },
        "messages": [
            {
                "id": "300000000000000001",
                "type": "ThreadCreated",
                "timestamp": "2024-01-17T08:00:00.000+00:00",
                "timestampEdited": None,
                "content": "",
                "author": {
                    "id": "600000000000000001",
                    "name": "Player1",
                    "discriminator": "0000",
                    "nickname": None,
                    "isBot": False,
                    "roles": [],
                    "avatarUrl": "",
                },
                "attachments": [],
                "embeds": [],
                "reactions": [],
                "mentions": [],
                "reference": None,
            }
        ],
        "messageCount": 1,
    }
    records = parse_channel(sys_data, TUPPER_NAMES)
    assert records[0]["tag"] == "system"


def test_empty_tupper_names_bot_is_proxy():
    """When tupper_names is empty (fallback), any bot is treated as a proxy."""
    records = parse_channel(FIXTURE_CHANNEL, set())
    # Message 2 is a bot — should be proxy even with empty set
    assert records[1]["tupperbox_proxy"] is True
    # Message 1 is not a bot
    assert records[0]["tupperbox_proxy"] is False


def test_write_output_jsonl(tmp_path: Path):
    """Integration: write fixture to tmp file via parse_channel, read back."""
    out = tmp_path / "messages_clean.jsonl"
    records = parse_channel(FIXTURE_CHANNEL, TUPPER_NAMES)
    with out.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    parsed = [json.loads(line) for line in lines]
    assert parsed[0]["tag"] == "IC"
    assert parsed[1]["tupperbox_proxy"] is True
    assert parsed[2]["tag"] == "OOC"
