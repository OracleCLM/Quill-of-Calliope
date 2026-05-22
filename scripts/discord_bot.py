#!/usr/bin/env python3
"""Quill of Calliope M4 Discord bot — semi-auto persona + char_memory + scene gen.

Extended (R-CALLIOPE-S-DISCORD-M4):
- Persona webhook proxy (Tupperbox-style) via discord_persona_binder.py
- /calliope-char-recall|remember|list — char_memory integration
- /calliope-draft|refine|blend — scene generation slash commands
- Auto-channels + rate limiting + whitelist privacy filter
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
import tempfile
from pathlib import Path
from typing import Optional

import aiohttp
import discord
from discord import app_commands

# ── Logging ───────────────────────────────────────────────────────────────────
_fmt = '{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}'
logging.basicConfig(
    level=logging.INFO,
    format=_fmt,
    handlers=[
        logging.FileHandler("/tmp/calliope_discord_bot.log"),
        logging.StreamHandler(sys.stderr),
    ],
)
log = logging.getLogger("calliope_bot")

# ── Config ────────────────────────────────────────────────────────────────────
_ENV_TOKEN = "CALLIOPE_DISCORD_BOT_TOKEN"
_STATE_DIR = Path(".planning/discord_state")
_WS_SERVER = "http://localhost:8767"
_SCRIPTS = Path(__file__).parent
_REPO_ROOT = _SCRIPTS.parent
_GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8766")
_VALID_STATES = {"idle", "talking", "listening", "thinking"}

# Auto-channels: comma-separated channel IDs where bot replies automatically
_AUTO_CHANNELS: set[int] = {
    int(x) for x in os.getenv("CALLIOPE_AUTO_CHANNELS", "").split(",") if x.strip().isdigit()
}
# Whitelist: channels allowed (empty = all allowed)
_WHITELIST_CHANNELS: set[int] = {
    int(x) for x in os.getenv("CALLIOPE_DISCORD_WHITELIST_CHANNELS", "").split(",")
    if x.strip().isdigit()
}

# Rate limiting: command → {user_id → last_call_time}
_RATE_LIMITS: dict[str, dict[int, float]] = {}
_COMMAND_COOLDOWN = 12.0
_CHANNEL_MSG_RATE: dict[int, list[float]] = {}
_MAX_MSG_PER_MIN = 5

# Eviction: prevent unbounded growth of rate-limit dicts on long-running bots.
# Why: audit P0 #3 found _RATE_LIMITS + _CHANNEL_MSG_RATE grow O(n_users,
# n_channels) without eviction → OOM after months of uptime.
_RATE_LIMIT_TTL = 60.0
_CLEANUP_INTERVAL = 300.0
_last_cleanup = 0.0

sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_REPO_ROOT))


def _cleanup_rate_state(force: bool = False) -> None:
    """Evict stale entries opportunistically; called from rate-limit checkers."""
    global _last_cleanup
    now_mono = time.monotonic()
    if not force and now_mono - _last_cleanup < _CLEANUP_INTERVAL:
        return
    _last_cleanup = now_mono
    for cmd, users in list(_RATE_LIMITS.items()):
        _RATE_LIMITS[cmd] = {u: t for u, t in users.items() if now_mono - t < _RATE_LIMIT_TTL}
        if not _RATE_LIMITS[cmd]:
            del _RATE_LIMITS[cmd]
    now_wall = time.time()
    for ch_id, ts_list in list(_CHANNEL_MSG_RATE.items()):
        fresh = [t for t in ts_list if now_wall - t < 60]
        if fresh:
            _CHANNEL_MSG_RATE[ch_id] = fresh
        else:
            del _CHANNEL_MSG_RATE[ch_id]


def _check_rate_limit(command: str, user_id: int) -> bool:
    """Return True if user is allowed (not rate limited)."""
    _cleanup_rate_state()
    now = time.monotonic()
    users = _RATE_LIMITS.setdefault(command, {})
    if now - users.get(user_id, 0.0) < _COMMAND_COOLDOWN:
        return False
    users[user_id] = now
    return True


def _check_channel_rate(channel_id: int) -> bool:
    """Return True if channel is below max msg/min threshold."""
    _cleanup_rate_state()
    now = time.time()
    ts = _CHANNEL_MSG_RATE.setdefault(channel_id, [])
    _CHANNEL_MSG_RATE[channel_id] = [t for t in ts if now - t < 60]
    if len(_CHANNEL_MSG_RATE[channel_id]) >= _MAX_MSG_PER_MIN:
        return False
    _CHANNEL_MSG_RATE[channel_id].append(now)
    return True


def _channel_allowed(channel_id: int) -> bool:
    """Privacy whitelist filter: empty whitelist = all channels allowed."""
    return (not _WHITELIST_CHANNELS) or (channel_id in _WHITELIST_CHANNELS)


def get_state_path(guild_id: int | str) -> Path:
    return _STATE_DIR / f"{guild_id}.json"


def load_guild_state(guild_id: int | str) -> Optional[object]:
    from narrative_state import NarrativeState  # noqa: PLC0415
    path = get_state_path(guild_id)
    if path.exists():
        try:
            return NarrativeState.load(path)
        except Exception as exc:
            log.warning("Failed loading state for guild %s: %s", guild_id, exc)
    return None


# ── Bot setup ─────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready() -> None:
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    await tree.sync()
    log.info("Connected as %s (id=%s)", client.user, client.user.id if client.user else "?")


@client.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return
    if not _channel_allowed(message.channel.id):
        return
    try:
        from discord_persona_binder import handle_persona_message  # noqa: PLC0415
        async with aiohttp.ClientSession() as sess:
            await handle_persona_message(message, client, session=sess)
    except Exception as exc:
        log.warning("persona_binder error (non-fatal): %s", exc)


# ── Helper: send long text ─────────────────────────────────────────────────────

async def _send_long(interaction: discord.Interaction, text: str, prefix: str = "") -> None:
    full = prefix + text
    if len(full) <= 1950:
        await interaction.followup.send(f"```md\n{full}```")
    else:
        import io  # noqa: PLC0415
        buf = io.BytesIO(full.encode("utf-8"))
        await interaction.followup.send(
            "Output (too long for message):",
            file=discord.File(buf, filename="calliope_output.md"),
        )


# ── char_memory slash commands ────────────────────────────────────────────────

@tree.command(name="calliope-char-recall", description="Recall char_memory facts for a character")
@app_commands.describe(name="Character name", query="Topic or event to recall")
async def calliope_char_recall(interaction: discord.Interaction, name: str, query: str) -> None:
    if not _channel_allowed(interaction.channel_id or 0):
        await interaction.response.send_message("Channel not whitelisted.", ephemeral=True)
        return
    if not _check_rate_limit("char_recall", interaction.user.id):
        await interaction.response.send_message("Rate limited — wait 12s.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        from app.calliope_shell.char_memory import retrieve_multi_signal  # noqa: PLC0415
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, retrieve_multi_signal, name, query, 3)
        if not results:
            await interaction.followup.send(f"No facts for **{name}** matching `{query}`.", ephemeral=True)
            return
        lines = [f"**Char recall**: {name} — `{query}`"]
        for i, r in enumerate(results, 1):
            lines.append(f"\n**{i}.** [{r['scope']}] score={r['score']:.2f}\n{r['fact_text'][:200]}")
        await interaction.followup.send("\n".join(lines), ephemeral=True)
    except Exception as exc:
        log.warning("char_recall error: %s", exc)
        await interaction.followup.send(f"Error: {exc}", ephemeral=True)


@tree.command(name="calliope-char-remember", description="Append a fact to char_memory")
@app_commands.describe(name="Character name", fact="Fact to remember")
async def calliope_char_remember(interaction: discord.Interaction, name: str, fact: str) -> None:
    if not _channel_allowed(interaction.channel_id or 0):
        await interaction.response.send_message("Channel not whitelisted.", ephemeral=True)
        return
    if not _check_rate_limit("char_remember", interaction.user.id):
        await interaction.response.send_message("Rate limited.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        from app.calliope_shell.char_memory_tools import char_memory_append  # noqa: PLC0415
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, char_memory_append, name, fact, "L1")
        if result.get("success"):
            await interaction.followup.send(
                f"✓ Remembered for **{name}** [L1]: `{fact[:100]}`\n"
                f"fact_id: `{result['fact_id'][:8]}`",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(f"✗ {result.get('error', 'unknown error')}", ephemeral=True)
    except Exception as exc:
        log.warning("char_remember error: %s", exc)
        await interaction.followup.send(f"Error: {exc}", ephemeral=True)


@tree.command(name="calliope-char-list", description="List all characters in char_memory")
async def calliope_char_list(interaction: discord.Interaction) -> None:
    if not _channel_allowed(interaction.channel_id or 0):
        await interaction.response.send_message("Channel not whitelisted.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        from app.calliope_shell.char_memory import list_chars  # noqa: PLC0415
        loop = asyncio.get_event_loop()
        chars = await loop.run_in_executor(None, list_chars)
        if not chars:
            await interaction.followup.send("No characters in memory DB.", ephemeral=True)
            return
        embed = discord.Embed(title="Calliope Characters", color=0x2c3e6b)
        for c in chars[:25]:
            embed.add_field(name=c["name"], value=c.get("traits_summary") or "—", inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as exc:
        log.warning("char_list error: %s", exc)
        await interaction.followup.send(f"Error: {exc}", ephemeral=True)


# ── Scene generation slash commands ──────────────────────────────────────────

@tree.command(name="calliope-draft", description="Generate a scene (with optional variants)")
@app_commands.describe(
    prompt="Scene context (IT/EN)",
    scene_type="Scene type (default: action_combat)",
    variants_n="Number of variants 1-5 (default 1)",
)
async def calliope_draft(
    interaction: discord.Interaction,
    prompt: str,
    scene_type: str = "action_combat",
    variants_n: int = 1,
) -> None:
    if not _channel_allowed(interaction.channel_id or 0):
        await interaction.response.send_message("Channel not whitelisted.", ephemeral=True)
        return
    if not _check_rate_limit("draft", interaction.user.id):
        await interaction.response.send_message("Rate limited — wait 12s.", ephemeral=True)
        return
    await interaction.response.defer()
    n = max(1, min(variants_n, 5))
    out_base = Path(f"/tmp/calliope_discord_{interaction.id}.md")
    cmd = [
        sys.executable, str(_SCRIPTS / "generate_scene.py"),
        "--scene-type", scene_type, "--prompt", prompt,
        "--gateway-url", _GATEWAY_URL, "--output", str(out_base),
    ]
    if n > 1:
        cmd += ["--variants", str(n)]
    try:
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        target = out_base.with_suffix(".variants.md") if n > 1 else out_base
        if not target.exists():
            target = out_base if out_base.exists() else None
        if target:
            content = target.read_text(encoding="utf-8")
            await _send_long(interaction, content, prefix=f"**Scene: {scene_type}**\n\n")
        else:
            err = (stderr or b"").decode(errors="replace")[:300]
            await interaction.followup.send(f"Generation failed: `{err}`")
    except asyncio.TimeoutError:
        await interaction.followup.send("Scene generation timed out (120s).")
    except Exception as exc:
        log.warning("draft error: %s", exc)
        await interaction.followup.send(f"Error: {exc}")


@tree.command(name="calliope-refine", description="Refine a scene with feedback")
@app_commands.describe(scene_text="Original scene text (paste)", feedback="Operator feedback (IT/EN)")
async def calliope_refine(
    interaction: discord.Interaction,
    scene_text: str,
    feedback: str,
) -> None:
    if not _channel_allowed(interaction.channel_id or 0):
        await interaction.response.send_message("Channel not whitelisted.", ephemeral=True)
        return
    if not _check_rate_limit("refine", interaction.user.id):
        await interaction.response.send_message("Rate limited.", ephemeral=True)
        return
    await interaction.response.defer()
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
        f.write(f"# Scene\n\n{scene_text}\n")
        tmp_in = f.name
    out_path = Path(f"/tmp/calliope_refine_{interaction.id}.md")
    cmd = [
        sys.executable, str(_SCRIPTS / "generate_scene.py"),
        "--refine", tmp_in, "--feedback", feedback,
        "--gateway-url", _GATEWAY_URL, "--output", str(out_path),
    ]
    try:
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await asyncio.wait_for(proc.communicate(), timeout=60)
        if out_path.exists():
            content = out_path.read_text(encoding="utf-8")
            await _send_long(interaction, content, prefix="**Refined scene:**\n\n")
        else:
            await interaction.followup.send("Refine failed — no output.")
    except asyncio.TimeoutError:
        await interaction.followup.send("Refine timed out (60s).")
    except Exception as exc:
        log.warning("refine error: %s", exc)
        await interaction.followup.send(f"Error: {exc}")
    finally:
        Path(tmp_in).unlink(missing_ok=True)


@tree.command(name="calliope-blend", description="Blend two scene texts into a hybrid")
@app_commands.describe(
    scene_v1="First scene text",
    scene_v2="Second scene text",
    hint="Optional blend instruction",
)
async def calliope_blend(
    interaction: discord.Interaction,
    scene_v1: str,
    scene_v2: str,
    hint: str = "",
) -> None:
    if not _channel_allowed(interaction.channel_id or 0):
        await interaction.response.send_message("Channel not whitelisted.", ephemeral=True)
        return
    if not _check_rate_limit("blend", interaction.user.id):
        await interaction.response.send_message("Rate limited.", ephemeral=True)
        return
    await interaction.response.defer()
    with tempfile.NamedTemporaryFile(suffix=".variants.md", mode="w", delete=False, encoding="utf-8") as f:
        f.write(
            "# Scene Variants: discord_blend\n\n---\n\n"
            f"## [V1] style=descriptive | latency=0ms\n\n{scene_v1}\n\n"
            f"## [V2] style=action-fast | latency=0ms\n\n{scene_v2}\n\n---\n"
        )
        tmp_variants = f.name
    out_path = Path(f"/tmp/calliope_blend_{interaction.id}.md")
    cmd = [
        sys.executable, str(_SCRIPTS / "blend_scene.py"),
        tmp_variants, "--blend", "1+2",
        "--gateway-url", _GATEWAY_URL, "--output", str(out_path),
    ]
    if hint:
        cmd += ["--hint", hint]
    try:
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await asyncio.wait_for(proc.communicate(), timeout=60)
        if out_path.exists():
            content = out_path.read_text(encoding="utf-8")
            await _send_long(interaction, content, prefix="**Blended scene:**\n\n")
        else:
            await interaction.followup.send("Blend failed — no output.")
    except asyncio.TimeoutError:
        await interaction.followup.send("Blend timed out (60s).")
    except Exception as exc:
        log.warning("blend error: %s", exc)
        await interaction.followup.send(f"Error: {exc}")
    finally:
        Path(tmp_variants).unlink(missing_ok=True)


# ── Legacy commands ───────────────────────────────────────────────────────────

@tree.command(name="mascot-state", description="Set mascot state")
@app_commands.describe(state="idle | talking | listening | thinking")
async def mascot_state(interaction: discord.Interaction, state: str) -> None:
    if state not in _VALID_STATES:
        await interaction.response.send_message(f"Invalid state. Choose: {', '.join(sorted(_VALID_STATES))}")
        return
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.post(f"{_WS_SERVER}/event/state", json={"state": state}, timeout=aiohttp.ClientTimeout(total=3)):
                pass
        await interaction.response.send_message(f"Mascot state updated: **{state}**")
    except Exception:
        await interaction.response.send_message("WS server unavailable.")


@tree.command(name="narrative-status", description="Show narrative state for this server")
async def narrative_status(interaction: discord.Interaction) -> None:
    gid = interaction.guild_id or 0
    state = load_guild_state(gid)
    if state:
        ctx = state.to_prompt_context()
        await interaction.response.send_message(f"```\n{ctx[:1900]}```")
    else:
        await interaction.response.send_message("No narrative state for this guild yet.")


@tree.command(name="narrative-reset", description="Reset guild narrative state (admin only)")
async def narrative_reset(interaction: discord.Interaction) -> None:
    if not interaction.user.guild_permissions.manage_guild:  # type: ignore[union-attr]
        await interaction.response.send_message("Insufficient permissions.")
        return
    path = get_state_path(interaction.guild_id or 0)
    if path.exists():
        path.unlink()
    await interaction.response.send_message("Narrative state reset.")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Calliope Discord bot M4")
    parser.add_argument("--sync-commands", action="store_true", help="Sync slash commands then exit")
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode")
    args = parser.parse_args()

    token = os.environ.get(_ENV_TOKEN)
    if not token:
        log.error(
            "Missing env var %s — get bot token from https://discord.com/developers/applications",
            _ENV_TOKEN,
        )
        sys.exit(1)

    if args.sync_commands:
        async def _sync() -> None:
            async with client:
                await tree.sync()
                log.info("Slash commands synced.")
        asyncio.run(_sync())
        return

    log.info("Starting Calliope bot M4. auto-channels=%s whitelist=%s",
             _AUTO_CHANNELS or "all", _WHITELIST_CHANNELS or "all")
    client.run(token)


if __name__ == "__main__":
    main()
