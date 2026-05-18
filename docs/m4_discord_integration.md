# Calliope.AI Discord Bot Integration — M4

## Overview

Discord bot for scene generation and mascot control. Slash commands trigger
`generate_scene.py` pipeline and WS server broadcasts to the Live2D frontend.

## Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. **New Application** → **Bot** tab → **Add Bot**
3. Under **Privileged Gateway Intents**, enable:
   - `MESSAGE_CONTENT`
   - `GUILD_MEMBERS`
4. Copy the bot token (Reset Token → Copy)
5. Set environment variable:
   ```bash
   export CALLIOPE_DISCORD_BOT_TOKEN="your_token_here"
   ```

## Invite Link

```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=2147485696&scope=bot+applications.commands
```

Replace `YOUR_CLIENT_ID` with the Application ID from the General Information tab.
Permissions integer `2147485696` = Send Messages + Use Slash Commands.

## Starting the Bot

```bash
# Start daemon
bash scripts/start_discord_bot.sh start

# Sync slash commands to Discord (run once after deploy)
python3 scripts/discord_bot.py --sync-commands

# Stop / status
bash scripts/start_discord_bot.sh stop
bash scripts/start_discord_bot.sh status
```

## Slash Commands

| Command | Description | Args | Example |
|---------|-------------|------|---------|
| `/scene-gen` | Generate a scene via LLM | `scene_type` (required), `prompt` (optional) | `/scene-gen action_combat Aurora fights at the gates` |
| `/mascot-state` | Set Live2D mascot state | `state`: idle\|talking\|listening\|thinking | `/mascot-state talking` |
| `/narrative-status` | Show current guild narrative state | — | `/narrative-status` |
| `/narrative-reset` | Reset guild narrative state | — (admin: Manage Guild) | `/narrative-reset` |

## Per-Guild State Architecture

- State files: `.planning/discord_state/<guild_id>.json`
- Schema: `NarrativeState` (chars, plot_threads, current_location, scene_count)
- Full isolation: each guild has its own file, no cross-guild leakage
- `load_guild_state(guild_id)` returns `None` if no state exists yet

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `Missing env var CALLIOPE_DISCORD_BOT_TOKEN` | Token not exported | `export CALLIOPE_DISCORD_BOT_TOKEN=...` |
| HTTP 403 from Discord | Missing intents | Enable MESSAGE_CONTENT + GUILD_MEMBERS in Portal |
| Slash commands not visible | Commands not synced | Run `python3 scripts/discord_bot.py --sync-commands` |
| WS server unavailable | mascot_ws_server not running | `bash scripts/start_mascot_ws.sh` |
