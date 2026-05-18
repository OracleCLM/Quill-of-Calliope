#!/usr/bin/env python3
"""Quill of Calliope M4 Discord bot — slash commands for scene gen + mascot control."""
from __future__ import annotations
import argparse
import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import aiohttp
import discord
from discord import app_commands

# ── Logging ──────────────────────────────────────────────────────────────────
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
CALLIOPE_DISCORD_BOT_TOKEN = "CALLIOPE_DISCORD_BOT_TOKEN"  # env var name
STATE_DIR = Path(".planning/discord_state")
WS_SERVER  = "http://localhost:8767"
_SCRIPTS   = Path(__file__).parent
_VALID_STATES = {"idle", "talking", "listening", "thinking"}

sys.path.insert(0, str(_SCRIPTS))
from narrative_state import NarrativeState  # noqa: E402


# ── Per-guild state helpers ───────────────────────────────────────────────────
def get_state_path(guild_id: int | str) -> Path:
    return STATE_DIR / f"{guild_id}.json"


def load_guild_state(guild_id: int | str) -> Optional[NarrativeState]:
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
tree   = app_commands.CommandTree(client)


@client.event
async def on_ready() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Logged in as %s (id=%s)", client.user, client.user.id if client.user else "?")


# ── Slash commands ────────────────────────────────────────────────────────────
@tree.command(name="scene-gen", description="Generate a scene")
@app_commands.describe(scene_type="Scene type (e.g. action_combat)", prompt="Optional scene prompt")
async def scene_gen(
    interaction: discord.Interaction,
    scene_type: str,
    prompt: Optional[str] = None,
) -> None:
    await interaction.response.defer()
    out_file = Path("/tmp/discord_scene.md")
    cmd = [
        sys.executable, str(_SCRIPTS / "generate_scene.py"),
        "--scene-type", scene_type,
        "--prompt", prompt or f"A {scene_type} scene in the Kingdom of Yokai.",
        "--output", str(out_file),
    ]
    try:
        subprocess.run(cmd, timeout=45, check=False)
        if not out_file.exists():
            await interaction.followup.send("Scene generation failed — no output file.")
            return
        content = out_file.read_text(encoding="utf-8")
        await interaction.followup.send(f"```md\n{content[:1900]}```")
    except Exception as exc:
        await interaction.followup.send(f"Error: {exc}")


@tree.command(name="mascot-state", description="Set mascot state")
@app_commands.describe(state="idle | talking | listening | thinking")
async def mascot_state(interaction: discord.Interaction, state: str) -> None:
    if state not in _VALID_STATES:
        await interaction.response.send_message(f"Invalid state. Choose: {', '.join(sorted(_VALID_STATES))}")
        return
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.post(f"{WS_SERVER}/event/state", json={"state": state}, timeout=aiohttp.ClientTimeout(total=3)):
                pass
        await interaction.response.send_message(f"Mascot state updated: **{state}**")
    except Exception:
        await interaction.response.send_message("WS server unavailable — state not broadcast.")


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
    parser = argparse.ArgumentParser(description="Calliope Discord bot")
    parser.add_argument("--sync-commands", action="store_true", help="Sync slash commands then exit")
    args = parser.parse_args()

    token = os.environ.get(CALLIOPE_DISCORD_BOT_TOKEN)
    if not token:
        log.error("Missing env var %s — set it before starting the bot.", CALLIOPE_DISCORD_BOT_TOKEN)
        sys.exit(1)

    if args.sync_commands:
        async def _sync() -> None:
            async with client:
                await tree.sync()
                log.info("Slash commands synced.")
        asyncio.run(_sync())
        return

    client.run(token)


if __name__ == "__main__":
    main()
