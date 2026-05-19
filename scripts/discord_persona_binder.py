"""Tupperbox-style persona webhook proxy for Quill of Calliope Discord bot.

Pattern: user sends "Aurora: She drew her sword" →
  bot deletes original + resends via webhook with Aurora avatar+name.

Ported pattern from Vesta/Minerva persona_binder (adapted for Calliope SQLite).
"""
from __future__ import annotations

import asyncio
import logging
import re
import sqlite3
import time
from pathlib import Path
from typing import Optional, Tuple

import discord
import yaml

log = logging.getLogger("calliope_persona_binder")

_REPO_ROOT = Path(__file__).parents[1]
_CHARS_DIR = _REPO_ROOT / "characters"
_DB_PATH = _REPO_ROOT / "data" / "discord_persona_config.db"

# Rate limiting: channel_id → last trigger timestamp
_PERSONA_COOLDOWNS: dict[int, float] = {}
_COOLDOWN_SECS = 2.0

# Trigger pattern: "CharName: text" (colon-space, char name = letters+spaces, no digit-only)
_TRIGGER_RE = re.compile(r"^([A-Za-zÀ-ÖØ-öø-ÿ][\w\s\-]{0,40}): (.{3,})$", re.DOTALL)


def init_db(db_path: Path = _DB_PATH) -> None:
    """Create webhook registry table if not exists."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS channel_webhooks (
                channel_id INTEGER PRIMARY KEY,
                webhook_url TEXT NOT NULL
            )
        """)


def _get_webhook_url(channel_id: int, db_path: Path = _DB_PATH) -> Optional[str]:
    try:
        with sqlite3.connect(str(db_path)) as c:
            row = c.execute(
                "SELECT webhook_url FROM channel_webhooks WHERE channel_id = ?",
                (channel_id,),
            ).fetchone()
        return row[0] if row else None
    except Exception as exc:
        log.warning("get_webhook_url failed: %s", exc)
        return None


def _save_webhook_url(channel_id: int, url: str, db_path: Path = _DB_PATH) -> None:
    try:
        with sqlite3.connect(str(db_path)) as c:
            c.execute(
                "INSERT OR REPLACE INTO channel_webhooks (channel_id, webhook_url) VALUES (?, ?)",
                (channel_id, url),
            )
    except Exception as exc:
        log.warning("save_webhook_url failed: %s", exc)


def delete_channel_webhook(channel_id: int, db_path: Path = _DB_PATH) -> bool:
    """Remove webhook entry for a channel."""
    try:
        with sqlite3.connect(str(db_path)) as c:
            c.execute("DELETE FROM channel_webhooks WHERE channel_id = ?", (channel_id,))
        return True
    except Exception as exc:
        log.warning("delete_channel_webhook failed: %s", exc)
        return False


def get_char_avatar(char_name: str) -> Optional[str]:
    """Read character YAML, return avatar_url or None. Case-insensitive file scan."""
    try:
        name_lower = char_name.lower().replace(" ", "-")
        for yaml_path in sorted(_CHARS_DIR.glob("*.yaml")):
            try:
                data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
                if not isinstance(data, dict):
                    continue
                file_name = data.get("name", "") or ""
                if file_name.lower() == char_name.lower() or yaml_path.stem.startswith(name_lower):
                    return data.get("avatar_url") or None
            except Exception:
                continue
    except Exception as exc:
        log.warning("get_char_avatar failed for %r: %s", char_name, exc)
    return None


def parse_persona_trigger(content: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse 'CharName: text' trigger. Returns (char_name, text) or (None, None)."""
    m = _TRIGGER_RE.match(content.strip())
    if not m:
        return None, None
    char_name, text = m.group(1).strip(), m.group(2).strip()
    # Reject all-digit names
    if char_name.replace(" ", "").isdigit():
        return None, None
    return char_name, text


def _is_known_char(char_name: str) -> bool:
    """Case-insensitive check vs char names in characters/*.yaml."""
    try:
        for yaml_path in _CHARS_DIR.glob("*.yaml"):
            try:
                data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
                if isinstance(data, dict):
                    name = data.get("name", "") or ""
                    if name.lower() == char_name.lower():
                        return True
            except Exception:
                continue
    except Exception:
        pass
    return False


async def get_or_create_webhook(
    channel: discord.TextChannel,
    bot_name: str,
    db_path: Path = _DB_PATH,
    session=None,
) -> Optional[discord.Webhook]:
    """Return existing webhook for channel or create one. Persists URL to DB."""
    loop = asyncio.get_event_loop()

    # Check DB cache
    url = await loop.run_in_executor(None, _get_webhook_url, channel.id, db_path)
    if url and session:
        try:
            return discord.Webhook.from_url(url, session=session)
        except Exception:
            pass

    # Scan existing webhooks on channel
    try:
        existing = await channel.webhooks()
        for wh in existing:
            if wh.name and "Calliope" in wh.name:
                if wh.url:
                    await loop.run_in_executor(None, _save_webhook_url, channel.id, wh.url, db_path)
                    if session:
                        return discord.Webhook.from_url(wh.url, session=session)
                    return wh
    except Exception as exc:
        log.warning("webhooks() failed: %s", exc)

    # Create new webhook
    try:
        wh = await channel.create_webhook(name=f"Calliope Persona ({bot_name})")
        if wh.url:
            await loop.run_in_executor(None, _save_webhook_url, channel.id, wh.url, db_path)
            if session:
                return discord.Webhook.from_url(wh.url, session=session)
        return wh
    except Exception as exc:
        log.warning("create_webhook failed on channel %s: %s", channel.id, exc)
        return None


async def handle_persona_message(
    message: discord.Message,
    bot_client: discord.Client,
    db_path: Path = _DB_PATH,
    session=None,
) -> bool:
    """Process potential persona trigger. Returns True if message was proxied."""
    if message.author.bot:
        return False

    char_name, text = parse_persona_trigger(message.content)
    if not char_name:
        return False

    # Rate limit per channel
    now = time.monotonic()
    last = _PERSONA_COOLDOWNS.get(message.channel.id, 0.0)
    if now - last < _COOLDOWN_SECS:
        return False
    _PERSONA_COOLDOWNS[message.channel.id] = now

    # Verify char is known
    loop = asyncio.get_event_loop()
    known = await loop.run_in_executor(None, _is_known_char, char_name)
    if not known:
        return False

    # Get or create webhook
    if not isinstance(message.channel, discord.TextChannel):
        return False
    wh = await get_or_create_webhook(message.channel, bot_client.user.name if bot_client.user else "Calliope", db_path, session)
    if not wh:
        log.warning("No webhook available for channel %s — skipping proxy", message.channel.id)
        return False

    # Delete original (fail-graceful)
    try:
        await message.delete()
    except discord.DiscordException as exc:
        log.warning("Could not delete message %s: %s", message.id, exc)

    # Get avatar
    avatar_url = await loop.run_in_executor(None, get_char_avatar, char_name)

    # Send via webhook
    try:
        await wh.send(
            content=text,
            username=char_name,
            avatar_url=avatar_url,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        log.info("Persona proxy: %s → webhook %s on channel %s", char_name, wh.id, message.channel.id)
        return True
    except discord.DiscordException as exc:
        log.warning("Webhook send failed: %s", exc)
        return False


# ── DB init on module load ────────────────────────────────────────────────────
init_db()
