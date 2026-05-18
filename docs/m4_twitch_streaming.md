# Calliope.AI — Twitch Streaming Integration

**Status**: M4 implemented — `scripts/twitch_bot.py` + `frontend/twitch_overlay/`
**Requires**: operator Twitch account + app registration

---

## 1. Twitch developer setup

### Register app
1. Go to https://dev.twitch.tv/console → **Register Your Application**
2. Name: `calliope-mascot`, OAuth redirect: `http://localhost`, Category: `Chat Bot`
3. Note: **Client ID** (needed for OAuth flow)

### Generate OAuth token (implicit flow)
```bash
# Open in browser — replace CLIENT_ID with yours:
https://id.twitch.tv/oauth2/authorize?client_id=CLIENT_ID&redirect_uri=http://localhost&response_type=token&scope=chat:read+chat:edit+channel:read:subscriptions

# After auth, copy token from URL fragment: #access_token=oauth:xxxx
```

Alternatively use Twitch CLI: `twitch token --user-token --scopes "chat:read chat:edit"`

---

## 2. Environment variables

Add to `.env` (project root) or `export` in shell:

```bash
CALLIOPE_TWITCH_TOKEN=oauth:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
CALLIOPE_TWITCH_CHANNEL=your_channel_name   # no # prefix
CALLIOPE_WS_URL=http://localhost:8767        # mascot WS server
```

---

## 3. OBS Studio — browser source

**Add Source → Browser Source:**

| Setting | Value |
|---------|-------|
| URL | `http://localhost:8080/frontend/twitch_overlay/index.html` |
| Width | 1920 |
| Height | 1080 |
| ✅ Transparent background | checked |
| Custom CSS | `body { background-color: transparent !important; }` |
| ✅ Shutdown source when not visible | checked |

**Position**: drag overlay to cover scene, set to bottom layer (mascot sits bottom-right, text top-left). Set source blend mode to **Alpha**.

---

## 4. Bot commands reference

| Command | Valid inputs | Effect |
|---------|-------------|--------|
| `!scene <type>` | `action_combat`, `lore_exposition`, `comedic_banter`, `mystery_investigation`, `intimate_dialogue`, `exploration_landscape`, `action_aftermath`, `dream_surreal`, `ritual_ceremony`, `combat_chase` | Mascot generates + displays scene text |
| `!mood <emotion>` | `neutral`, `happy`, `sad`, `angry`, `fearful`, `determined` | Changes mascot expression |

**Cooldown**: 5s per user for both commands.

**Auto-triggers**:
- New subscriber → mascot = `surprise` + chat message
- Raid → mascot = `happy` + raid announcement

---

## 5. Full streaming workflow

```bash
# 1. Start all daemons (LLM gateway :8766 + mascot WS :8767)
bash scripts/start_all_calliope_daemons.sh

# 2. Start HTTP dev server (serves overlay to OBS)
python3 -m http.server 8080 &

# 3. Start Twitch bot
bash scripts/start_twitch_bot.sh

# 4. Verify everything running
bash scripts/start_mascot_ws.sh --status
curl -s http://localhost:8766/health

# 5. Open OBS → add Browser Source (see §3) → Go Live
```

**Stop all:**
```bash
bash scripts/stop_all_calliope_daemons.sh
bash scripts/start_twitch_bot.sh --stop
```

---

## 6. Troubleshooting

| Problem | Fix |
|---------|-----|
| Bot not in chat | Check `CALLIOPE_TWITCH_TOKEN` starts with `oauth:` — check `/tmp/calliope_twitch_bot.log` |
| OBS browser source black | Enable "Transparent background" + add custom CSS |
| OBS browser caching old JS | Right-click source → Properties → hit OK to force reload |
| Mascot not appearing | Confirm cubism.live2d.com CDN reachable; check browser console via OBS Tools → Interact |
| WebSocket disconnect loop | Check `start_mascot_ws.sh --status`; bot auto-reconnects every 3s |
| Token expired | OAuth user tokens expire after 60 days; regenerate via §1 flow |
| `!scene` no response | LLM gateway :8766 may be down — `curl http://localhost:8766/health` |
