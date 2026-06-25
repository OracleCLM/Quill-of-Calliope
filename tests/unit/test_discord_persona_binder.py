"""Unit test per scripts/discord_persona_binder.py — parse_persona_trigger (pura)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from scripts.discord_persona_binder import (
    _get_webhook_url,
    _is_known_char,
    _save_webhook_url,
    delete_channel_webhook,
    get_char_avatar,
    init_db,
    parse_persona_trigger,
)


def test_valid_simple():
    assert parse_persona_trigger("Alice: Hello world") == ("Alice", "Hello world")


def test_valid_with_spaces_in_name():
    assert parse_persona_trigger("John Doe: Hello world") == ("John Doe", "Hello world")


def test_valid_strip_outer_whitespace():
    assert parse_persona_trigger("  John Doe : Hello world  ") == ("John Doe", "Hello world")


def test_valid_unicode_name():
    assert parse_persona_trigger("Élise: Bonjour!") == ("Élise", "Bonjour!")


def test_valid_min_text_length():
    assert parse_persona_trigger("A: Hey") == ("A", "Hey")


def test_valid_dotall_newlines():
    result = parse_persona_trigger("Alice: text with\nnewlines")
    assert result == ("Alice", "text with\nnewlines")


def test_no_match_missing_space_after_colon():
    assert parse_persona_trigger("Alice:Hello world") == (None, None)


def test_no_match_text_too_short():
    assert parse_persona_trigger("A: Hi") == (None, None)


def test_no_match_digit_start():
    assert parse_persona_trigger("123: hello world") == (None, None)


def test_no_match_name_too_long():
    long_name = "A" * 42
    assert parse_persona_trigger(f"{long_name}: test") == (None, None)


def test_no_match_empty_string():
    assert parse_persona_trigger("") == (None, None)


def test_no_match_whitespace_only():
    assert parse_persona_trigger("  \t  ") == (None, None)


def test_parse_persona_trigger_digit_name_rejected() -> None:
    """Line 109: char_name all-digit → (None, None). Raggiunto via mock del regex."""
    mock_match = MagicMock()
    mock_match.group.side_effect = lambda n: "123" if n == 1 else "hello world"
    with patch("scripts.discord_persona_binder._TRIGGER_RE") as mock_re:
        mock_re.match.return_value = mock_match
        assert parse_persona_trigger("trigger") == (None, None)


# ── SQLite helpers ────────────────────────────────────────────────────────────

def test_get_webhook_url_not_found(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    init_db(db)
    assert _get_webhook_url(1, db) is None


def test_save_and_get_webhook_url(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    init_db(db)
    _save_webhook_url(1, "http://example.com/hook", db)
    assert _get_webhook_url(1, db) == "http://example.com/hook"


def test_save_webhook_url_upserts(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    init_db(db)
    _save_webhook_url(1, "http://v1.example.com", db)
    _save_webhook_url(1, "http://v2.example.com", db)
    assert _get_webhook_url(1, db) == "http://v2.example.com"


def test_delete_channel_webhook_removes_entry(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    init_db(db)
    _save_webhook_url(1, "http://example.com/hook", db)
    assert delete_channel_webhook(1, db) is True
    assert _get_webhook_url(1, db) is None


def test_get_webhook_url_exception_returns_none() -> None:
    assert _get_webhook_url(1, Path("/nonexistent_dir/test.db")) is None


def test_save_webhook_url_exception_silent() -> None:
    _save_webhook_url(1, "url", Path("/nonexistent_dir/test.db"))


def test_delete_channel_webhook_exception_returns_false() -> None:
    assert delete_channel_webhook(1, Path("/nonexistent_dir/test.db")) is False


# ── get_char_avatar ───────────────────────────────────────────────────────────

def test_get_char_avatar_match_name(tmp_path: Path) -> None:
    (tmp_path / "aurora.yaml").write_text(yaml.dump({"name": "Aurora", "avatar_url": "aurora.png"}))
    with patch("scripts.discord_persona_binder._CHARS_DIR", tmp_path):
        assert get_char_avatar("Aurora") == "aurora.png"


def test_get_char_avatar_match_stem(tmp_path: Path) -> None:
    (tmp_path / "aurora-dark.yaml").write_text(yaml.dump({"name": "Other", "avatar_url": "dark.png"}))
    with patch("scripts.discord_persona_binder._CHARS_DIR", tmp_path):
        assert get_char_avatar("aurora dark") == "dark.png"


def test_get_char_avatar_no_avatar_url(tmp_path: Path) -> None:
    (tmp_path / "luna.yaml").write_text(yaml.dump({"name": "Luna"}))
    with patch("scripts.discord_persona_binder._CHARS_DIR", tmp_path):
        assert get_char_avatar("Luna") is None


def test_get_char_avatar_not_found(tmp_path: Path) -> None:
    with patch("scripts.discord_persona_binder._CHARS_DIR", tmp_path):
        assert get_char_avatar("Ghost") is None


def test_get_char_avatar_invalid_yaml(tmp_path: Path) -> None:
    (tmp_path / "bad.yaml").write_text("{: invalid yaml [")
    with patch("scripts.discord_persona_binder._CHARS_DIR", tmp_path):
        assert get_char_avatar("bad") is None


def test_get_char_avatar_chars_dir_missing() -> None:
    with patch("scripts.discord_persona_binder._CHARS_DIR", Path("/nonexistent_chars_dir")):
        assert get_char_avatar("Any") is None


def test_get_char_avatar_non_dict_yaml(tmp_path: Path) -> None:
    (tmp_path / "list.yaml").write_text(yaml.dump(["a", "b"]))
    with patch("scripts.discord_persona_binder._CHARS_DIR", tmp_path):
        assert get_char_avatar("list") is None


# ── _is_known_char ────────────────────────────────────────────────────────────

def test_is_known_char_true(tmp_path: Path) -> None:
    (tmp_path / "alice.yaml").write_text(yaml.dump({"name": "Alice"}))
    with patch("scripts.discord_persona_binder._CHARS_DIR", tmp_path):
        assert _is_known_char("Alice") is True


def test_is_known_char_case_insensitive(tmp_path: Path) -> None:
    (tmp_path / "alice.yaml").write_text(yaml.dump({"name": "Alice"}))
    with patch("scripts.discord_persona_binder._CHARS_DIR", tmp_path):
        assert _is_known_char("alice") is True


def test_is_known_char_false(tmp_path: Path) -> None:
    (tmp_path / "alice.yaml").write_text(yaml.dump({"name": "Alice"}))
    with patch("scripts.discord_persona_binder._CHARS_DIR", tmp_path):
        assert _is_known_char("Bob") is False


def test_is_known_char_invalid_yaml(tmp_path: Path) -> None:
    (tmp_path / "bad.yaml").write_text("{: invalid [")
    with patch("scripts.discord_persona_binder._CHARS_DIR", tmp_path):
        assert _is_known_char("bad") is False


def test_is_known_char_chars_dir_missing() -> None:
    with patch("scripts.discord_persona_binder._CHARS_DIR", Path("/nonexistent_chars_dir")):
        assert _is_known_char("Any") is False


def test_get_char_avatar_glob_exception() -> None:
    """Lines 96-97: outer except se glob() raises."""
    mock_dir = MagicMock(spec=Path)
    mock_dir.glob.side_effect = PermissionError("no access")
    with patch("scripts.discord_persona_binder._CHARS_DIR", mock_dir):
        assert get_char_avatar("Any") is None


def test_is_known_char_glob_exception() -> None:
    """Lines 125-126: outer except se glob() raises."""
    mock_dir = MagicMock(spec=Path)
    mock_dir.glob.side_effect = PermissionError("no access")
    with patch("scripts.discord_persona_binder._CHARS_DIR", mock_dir):
        assert _is_known_char("Any") is False


# ── async: handle_persona_message paths (senza webhook) ─────────────────────

import asyncio  # noqa: E402
from unittest.mock import AsyncMock  # noqa: E402

from scripts.discord_persona_binder import handle_persona_message  # noqa: E402
import scripts.discord_persona_binder as _mod  # noqa: E402


def test_handle_persona_message_bot_skipped() -> None:
    """Line 181: message.author.bot=True → False."""
    msg = MagicMock()
    msg.author.bot = True
    assert asyncio.run(handle_persona_message(msg, MagicMock())) is False


def test_handle_persona_message_no_trigger() -> None:
    """Lines 183-185: no parse trigger → False."""
    msg = MagicMock()
    msg.author.bot = False
    msg.content = "just a normal sentence without colon"
    assert asyncio.run(handle_persona_message(msg, MagicMock())) is False


def test_handle_persona_message_cooldown_blocks(tmp_path) -> None:
    """Lines 190-191: cooldown hit → False."""
    import time
    _mod._PERSONA_COOLDOWNS[55555] = time.monotonic()  # set cooldown now
    msg = MagicMock()
    msg.author.bot = False
    msg.content = "Alice: She drew her sword"
    msg.channel.id = 55555
    assert asyncio.run(handle_persona_message(msg, MagicMock())) is False
    _mod._PERSONA_COOLDOWNS.pop(55555, None)


def test_handle_persona_message_unknown_char(tmp_path) -> None:
    """Lines 196-198: char not in YAML → False."""
    _mod._PERSONA_COOLDOWNS.clear()
    msg = MagicMock()
    msg.author.bot = False
    msg.content = "Alice: She drew her sword"
    msg.channel.id = 66666
    with patch("scripts.discord_persona_binder._CHARS_DIR", tmp_path):
        assert asyncio.run(handle_persona_message(msg, MagicMock())) is False


def test_handle_persona_message_not_text_channel(tmp_path) -> None:
    """Lines 201-202: channel not TextChannel → False."""
    _mod._PERSONA_COOLDOWNS.clear()
    (tmp_path / "alice.yaml").write_text(yaml.dump({"name": "Alice"}))
    msg = MagicMock()
    msg.author.bot = False
    msg.content = "Alice: She drew her sword"
    msg.channel = MagicMock()  # channel.id è MagicMock auto
    _UniqueClass = type("_UniqueTextChannelClass", (), {})
    with patch("scripts.discord_persona_binder._CHARS_DIR", tmp_path), \
         patch("scripts.discord_persona_binder._is_known_char", return_value=True), \
         patch("scripts.discord_persona_binder.discord") as md:
        md.TextChannel = _UniqueClass  # isinstance(MagicMock(), _UniqueClass) = False
        md.DiscordException = Exception
        result = asyncio.run(handle_persona_message(msg, MagicMock()))
    assert result is False


def _patched_discord_ctx(ctx_mock):
    """Patch discord nel modulo in modo che isinstance(any, TextChannel) = True."""
    ctx_mock.TextChannel = object
    ctx_mock.DiscordException = Exception
    ctx_mock.AllowedMentions.none.return_value = None
    return ctx_mock


def test_handle_persona_message_success(tmp_path) -> None:
    """Lines 203-226: proxy completo — delete + webhook send."""
    _mod._PERSONA_COOLDOWNS.clear()
    (tmp_path / "alice.yaml").write_text(yaml.dump({"name": "Alice"}))
    db = tmp_path / "test.db"
    init_db(db)
    msg = MagicMock()
    msg.author.bot = False
    msg.content = "Alice: She drew her sword from the scabbard"
    msg.channel.id = 88001
    msg.delete = AsyncMock()
    mock_wh = MagicMock()
    mock_wh.send = AsyncMock()
    mock_wh.id = 1
    with patch("scripts.discord_persona_binder._CHARS_DIR", tmp_path), \
         patch("scripts.discord_persona_binder._is_known_char", return_value=True), \
         patch("scripts.discord_persona_binder.discord") as md, \
         patch("scripts.discord_persona_binder.get_or_create_webhook",
               new_callable=AsyncMock, return_value=mock_wh):
        _patched_discord_ctx(md)
        result = asyncio.run(handle_persona_message(msg, MagicMock(), db_path=db))
    assert result is True
    mock_wh.send.assert_called_once()


def test_handle_persona_message_no_webhook_returns_false(tmp_path) -> None:
    """Lines 204-206: get_or_create_webhook → None → False."""
    _mod._PERSONA_COOLDOWNS.clear()
    (tmp_path / "alice.yaml").write_text(yaml.dump({"name": "Alice"}))
    db = tmp_path / "test.db"
    init_db(db)
    msg = MagicMock()
    msg.author.bot = False
    msg.content = "Alice: She drew her sword from scabbard"
    msg.channel.id = 88002
    with patch("scripts.discord_persona_binder._CHARS_DIR", tmp_path), \
         patch("scripts.discord_persona_binder._is_known_char", return_value=True), \
         patch("scripts.discord_persona_binder.discord") as md, \
         patch("scripts.discord_persona_binder.get_or_create_webhook",
               new_callable=AsyncMock, return_value=None):
        _patched_discord_ctx(md)
        result = asyncio.run(handle_persona_message(msg, MagicMock(), db_path=db))
    assert result is False


def test_handle_persona_message_delete_fails_still_proxies(tmp_path) -> None:
    """Lines 209-212: delete raises → log + continua con send."""
    _mod._PERSONA_COOLDOWNS.clear()
    (tmp_path / "alice.yaml").write_text(yaml.dump({"name": "Alice"}))
    db = tmp_path / "test.db"
    init_db(db)
    msg = MagicMock()
    msg.author.bot = False
    msg.content = "Alice: She drew her sword from scabbard"
    msg.channel.id = 88003
    msg.delete = AsyncMock(side_effect=Exception("Cannot delete"))
    mock_wh = MagicMock()
    mock_wh.send = AsyncMock()
    mock_wh.id = 2
    with patch("scripts.discord_persona_binder._CHARS_DIR", tmp_path), \
         patch("scripts.discord_persona_binder._is_known_char", return_value=True), \
         patch("scripts.discord_persona_binder.discord") as md, \
         patch("scripts.discord_persona_binder.get_or_create_webhook",
               new_callable=AsyncMock, return_value=mock_wh):
        _patched_discord_ctx(md)
        result = asyncio.run(handle_persona_message(msg, MagicMock(), db_path=db))
    assert result is True


def test_handle_persona_message_send_fails_returns_false(tmp_path) -> None:
    """Lines 227-229: wh.send raises DiscordException → False."""
    _mod._PERSONA_COOLDOWNS.clear()
    (tmp_path / "alice.yaml").write_text(yaml.dump({"name": "Alice"}))
    db = tmp_path / "test.db"
    init_db(db)
    msg = MagicMock()
    msg.author.bot = False
    msg.content = "Alice: She drew her sword from scabbard"
    msg.channel.id = 88004
    msg.delete = AsyncMock()
    mock_wh = MagicMock()
    mock_wh.send = AsyncMock(side_effect=Exception("Send failed"))
    mock_wh.id = 3
    with patch("scripts.discord_persona_binder._CHARS_DIR", tmp_path), \
         patch("scripts.discord_persona_binder._is_known_char", return_value=True), \
         patch("scripts.discord_persona_binder.discord") as md, \
         patch("scripts.discord_persona_binder.get_or_create_webhook",
               new_callable=AsyncMock, return_value=mock_wh):
        _patched_discord_ctx(md)
        result = asyncio.run(handle_persona_message(msg, MagicMock(), db_path=db))
    assert result is False


# ── get_or_create_webhook ─────────────────────────────────────────────────────

from scripts.discord_persona_binder import get_or_create_webhook  # noqa: E402


def test_get_or_create_webhook_from_db_cache_with_session(tmp_path) -> None:
    """Lines 140-145: URL in DB + session → from_url return."""
    db = tmp_path / "test.db"
    init_db(db)
    _save_webhook_url(9001, "https://discord.com/api/webhooks/123/abc", db)
    channel = MagicMock()
    channel.id = 9001
    mock_session = MagicMock()
    with patch("scripts.discord_persona_binder.discord") as md:
        md.Webhook.from_url.return_value = MagicMock()
        result = asyncio.run(get_or_create_webhook(channel, "Bot", db_path=db, session=mock_session))
    md.Webhook.from_url.assert_called_once()
    assert result is not None


def test_get_or_create_webhook_scans_existing_calliope(tmp_path) -> None:
    """Lines 148-156: scan existing webhooks, trova Calliope → return it."""
    db = tmp_path / "test.db"
    init_db(db)
    mock_wh = MagicMock()
    mock_wh.url = "https://discord.com/api/webhooks/exists/hook"
    mock_wh.name = "Calliope Persona (TestBot)"
    channel = MagicMock()
    channel.id = 9002
    channel.webhooks = AsyncMock(return_value=[mock_wh])
    result = asyncio.run(get_or_create_webhook(channel, "TestBot", db_path=db))
    assert result == mock_wh


def test_get_or_create_webhook_scan_fails_then_creates(tmp_path) -> None:
    """Lines 157-158 + 161-167: channel.webhooks() raises → crea nuovo."""
    db = tmp_path / "test.db"
    init_db(db)
    mock_wh = MagicMock()
    mock_wh.url = "https://discord.com/api/webhooks/new/hook"
    channel = MagicMock()
    channel.id = 9003
    channel.webhooks = AsyncMock(side_effect=Exception("Forbidden"))
    channel.create_webhook = AsyncMock(return_value=mock_wh)
    result = asyncio.run(get_or_create_webhook(channel, "Bot", db_path=db))
    assert result == mock_wh


def test_get_or_create_webhook_creates_new(tmp_path) -> None:
    """Lines 161-167: no existing → create_webhook."""
    db = tmp_path / "test.db"
    init_db(db)
    mock_wh = MagicMock()
    mock_wh.url = "https://discord.com/api/webhooks/brand/new"
    channel = MagicMock()
    channel.id = 9004
    channel.webhooks = AsyncMock(return_value=[])
    channel.create_webhook = AsyncMock(return_value=mock_wh)
    result = asyncio.run(get_or_create_webhook(channel, "Bot", db_path=db))
    assert result == mock_wh
    channel.create_webhook.assert_called_once()


def test_get_or_create_webhook_create_fails_returns_none(tmp_path) -> None:
    """Lines 168-170: create_webhook raises → return None."""
    db = tmp_path / "test.db"
    init_db(db)
    channel = MagicMock()
    channel.id = 9005
    channel.webhooks = AsyncMock(return_value=[])
    channel.create_webhook = AsyncMock(side_effect=Exception("Permission denied"))
    result = asyncio.run(get_or_create_webhook(channel, "Bot", db_path=db))
    assert result is None


def test_get_or_create_webhook_from_url_raises_fallthrough(tmp_path) -> None:
    """Lines 144-145: from_url raises → except pass → continua a cercare webhooks."""
    db = tmp_path / "test.db"
    init_db(db)
    _save_webhook_url(9006, "https://discord.com/api/webhooks/123/abc", db)
    mock_wh = MagicMock()
    mock_wh.url = "https://discord.com/api/webhooks/new/hook"
    channel = MagicMock()
    channel.id = 9006
    channel.webhooks = AsyncMock(return_value=[])
    channel.create_webhook = AsyncMock(return_value=mock_wh)
    mock_session = MagicMock()
    with patch("scripts.discord_persona_binder.discord") as md:
        md.Webhook.from_url.side_effect = [Exception("Invalid URL"), MagicMock()]
        result = asyncio.run(get_or_create_webhook(channel, "Bot", db_path=db, session=mock_session))
    assert result is not None  # fallthrough a create_webhook, seconda from_url ha successo


def test_get_or_create_webhook_existing_with_session(tmp_path) -> None:
    """Line 155: existing Calliope webhook + session → from_url."""
    db = tmp_path / "test.db"
    init_db(db)
    existing_wh = MagicMock()
    existing_wh.url = "https://discord.com/api/webhooks/99/tok"
    existing_wh.name = "Calliope Persona (Bot)"
    channel = MagicMock()
    channel.id = 9007
    channel.webhooks = AsyncMock(return_value=[existing_wh])
    mock_session = MagicMock()
    with patch("scripts.discord_persona_binder.discord") as md:
        md.Webhook.from_url.return_value = MagicMock()
        result = asyncio.run(get_or_create_webhook(channel, "Bot", db_path=db, session=mock_session))
    md.Webhook.from_url.assert_called()
    assert result is not None


def test_get_or_create_webhook_new_with_session(tmp_path) -> None:
    """Line 166: create_webhook + session → from_url."""
    db = tmp_path / "test.db"
    init_db(db)
    new_wh = MagicMock()
    new_wh.url = "https://discord.com/api/webhooks/new/tok2"
    channel = MagicMock()
    channel.id = 9008
    channel.webhooks = AsyncMock(return_value=[])
    channel.create_webhook = AsyncMock(return_value=new_wh)
    mock_session = MagicMock()
    with patch("scripts.discord_persona_binder.discord") as md:
        md.Webhook.from_url.return_value = MagicMock()
        result = asyncio.run(get_or_create_webhook(channel, "Bot", db_path=db, session=mock_session))
    md.Webhook.from_url.assert_called()
    assert result is not None
