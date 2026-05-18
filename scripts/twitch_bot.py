#!/usr/bin/env python3
"""Quill of Calliope Twitch bot — mascot state control via chat commands.

Architecture:
  - Pure logic (testable, no twitchio dependency): VALID_*, check_cooldown, push_event
  - CalliopeBot(twitchio.ext.commands.Bot): thin IRC wrapper around pure logic

twitchio 3.x requires: client_id, client_secret (Twitch dev console app).
See docs/m4_twitch_streaming.md for setup.
"""

import os
import sys
import time
from typing import Optional

import httpx

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Pure constants (imported by tests) ───────────────────────────────────────

VALID_SCENE_TYPES = frozenset({
    "action_combat", "lore_exposition", "comedic_banter", "mystery_investigation",
    "intimate_dialogue", "exploration_landscape", "action_aftermath",
    "dream_surreal", "ritual_ceremony", "combat_chase",
})

VALID_EMOTIONS = frozenset({"neutral", "happy", "sad", "angry", "fearful", "determined"})

COOLDOWN_SEC = 5.0


# ── Pure logic (no twitchio) ─────────────────────────────────────────────────

def check_cooldown(cooldowns: dict, user_id: str, cooldown_sec: float = COOLDOWN_SEC) -> bool:
    """Return True if user may act (and update timestamp). False if still cooling down."""
    now = time.monotonic()
    if now - cooldowns.get(user_id, 0.0) >= cooldown_sec:
        cooldowns[user_id] = now
        return True
    return False


async def push_event(ws_url: str, payload: dict) -> None:
    """POST event JSON to mascot WS server. Silent on error."""
    url = f"{ws_url.rstrip('/')}/twitch-event"
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, timeout=5.0)
    except Exception as exc:
        print(f"[twitch_bot] Warning: push_event failed: {exc}")


def build_scene_payload(scene_type: str, username: str) -> dict:
    return {"event": "scene_request", "scene_type": scene_type, "user": username}


def build_mood_payload(emotion: str, username: str) -> dict:
    return {"event": "mood_change", "emotion": emotion, "user": username}


def build_state_payload(state: str) -> dict:
    return {"event": "mascot_state", "state": state}


# ── twitchio Bot wrapper ──────────────────────────────────────────────────────

def _make_bot(client_id: str, client_secret: str, bot_id: str,
              channel: str, ws_url: str):
    """Factory: import twitchio and construct CalliopeBot."""
    from twitchio.ext.commands import Bot, Context, command  # noqa: PLC0415

    class CalliopeBot(Bot):
        def __init__(self) -> None:
            super().__init__(
                client_id=client_id,
                client_secret=client_secret,
                bot_id=bot_id,
                prefix="!",
            )
            self.channel_name = channel
            self.ws_url = ws_url
            self._cooldowns: dict[str, float] = {}

        async def event_ready(self) -> None:
            print(f"[CalliopeBot] Ready — watching #{self.channel_name}")

        async def event_message(self, message) -> None:
            if message.echo:
                return
            await self.handle_commands(message)

        @command()
        async def scene(self, ctx: Context, scene_type: Optional[str] = None) -> None:
            if not scene_type:
                await ctx.send("Usage: !scene <type> — try: action_combat, lore_exposition …")
                return
            stype = scene_type.lower()
            if stype not in VALID_SCENE_TYPES:
                await ctx.send(f"Unknown scene type. Try: {', '.join(sorted(VALID_SCENE_TYPES))}")
                return
            username = ctx.author.display_name
            if not check_cooldown(self._cooldowns, str(ctx.author.id)):
                await ctx.send(f"@{username}, please wait {COOLDOWN_SEC:.0f}s.")
                return
            await push_event(self.ws_url, build_scene_payload(stype, username))
            await ctx.send(f"Generating {stype} scene for @{username}!")

        @command()
        async def mood(self, ctx: Context, emotion: Optional[str] = None) -> None:
            if not emotion:
                await ctx.send(f"Usage: !mood — options: {', '.join(sorted(VALID_EMOTIONS))}")
                return
            emo = emotion.lower()
            if emo not in VALID_EMOTIONS:
                await ctx.send(f"Invalid emotion. Choose: {', '.join(sorted(VALID_EMOTIONS))}")
                return
            username = ctx.author.display_name
            if not check_cooldown(self._cooldowns, str(ctx.author.id)):
                await ctx.send(f"@{username}, please wait.")
                return
            await push_event(self.ws_url, build_mood_payload(emo, username))
            await ctx.send(f"Mascot mood → {emo} 🎭")

        async def event_usernotice(self, notice) -> None:
            channel = notice.channel
            user = notice.user
            if not channel or not user:
                return
            msg_id = (notice.tags or {}).get("msg-id", "")
            if msg_id in ("sub", "resub", "subgift"):
                await push_event(self.ws_url, build_state_payload("surprise"))
                await channel.send(f"Welcome subscriber @{user.display_name}! 🎉")
            elif msg_id == "raid":
                viewers = (notice.tags or {}).get("msg-param-viewerCount", "?")
                await push_event(self.ws_url, build_state_payload("happy"))
                await channel.send(f"Raid from @{user.display_name} with {viewers} viewers! 🚀")

    return CalliopeBot()


def main() -> None:
    client_id = os.getenv("CALLIOPE_TWITCH_CLIENT_ID", "").strip()
    client_secret = os.getenv("CALLIOPE_TWITCH_CLIENT_SECRET", "").strip()
    bot_id = os.getenv("CALLIOPE_TWITCH_BOT_ID", "").strip()
    channel = os.getenv("CALLIOPE_TWITCH_CHANNEL", "").strip().lstrip("#")
    ws_url = os.getenv("CALLIOPE_WS_URL", "http://localhost:8767")

    missing = [k for k, v in {
        "CALLIOPE_TWITCH_CLIENT_ID": client_id,
        "CALLIOPE_TWITCH_CLIENT_SECRET": client_secret,
        "CALLIOPE_TWITCH_BOT_ID": bot_id,
        "CALLIOPE_TWITCH_CHANNEL": channel,
    }.items() if not v]
    if missing:
        print(f"ERROR: Missing env vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    bot = _make_bot(client_id, client_secret, bot_id, channel, ws_url)
    bot.run()


if __name__ == "__main__":
    main()
