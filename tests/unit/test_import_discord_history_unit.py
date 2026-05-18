import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
from import_discord_history import parse_channel, _classify_tag, _load_tupper_names

def _make_msg(id="1", content="Hello", type_="Default", ref=None, is_bot=False, nick=None):
    return {"id": id, "type": type_, "timestamp": "2024-01-01T00:00:00Z",
            "timestampEdited": None, "content": content,
            "author": {"id": "u1", "name": "alice", "discriminator": "0000",
                       "nickname": nick, "isBot": is_bot, "roles": [], "avatarUrl": ""},
            "attachments": [], "reactions": [], "mentions": [],
            "reference": ref}

def _make_data(msgs, channel_type="GuildTextChat", category_id=None):
    ch = {"id": "c1", "name": "test", "type": channel_type, "topic": ""}
    if category_id: ch["categoryId"] = category_id
    return {"guild": {"id": "g1", "name": "KoY"}, "channel": ch,
            "messages": msgs, "messageCount": len(msgs)}

def test_reply_to_set():
    msg = _make_msg(ref={"messageId": "99", "channelId": "c1", "guildId": "g1"})
    r = parse_channel(_make_data([msg]), set())
    assert r[0]["reply_to"] == "99"

def test_thread_parent_channel_id():
    data = _make_data([_make_msg()], channel_type="GuildPublicThread", category_id="parent_ch")
    r = parse_channel(data, set())
    assert r[0]["parent_channel_id"] == "parent_ch"

def test_classify_system_types():
    assert _classify_tag("ThreadCreated", "") == "system"
    assert _classify_tag("ChannelPinnedMessage", "") == "system"

def test_classify_ooc_bracket():
    assert _classify_tag("Default", "[OOC] chat") == "OOC"

def test_classify_default_ic():
    assert _classify_tag("Default", "Normal RP text") == "IC"

def test_load_tupper_names_missing():
    result = _load_tupper_names(Path("/tmp/nonexistent_tuppers_xyz.json"))
    assert result == set()

def test_parse_empty_messages():
    r = parse_channel(_make_data([]), set())
    assert r == []

def test_tupperbox_proxy_detected():
    msg = _make_msg(is_bot=True)
    r = parse_channel(_make_data([msg]), {"alice"})  # alice is tupper name
    assert r[0]["tupperbox_proxy"] is True
