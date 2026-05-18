# Discord Import Runbook — Kingdom of Yokai

End-to-end procedure: Discord server → datasets locali per Quill of Calliope.

---

## Layout

| Componente | Tool | Path |
|---|---|---|
| Messaggi canali + threads | DiscordChatExporter 2.47.1 | `~/.local/share/dce/` (symlink `~/.local/bin/dce`) |
| Server roles + members + channel overwrites | `vile/discord-role-scraper` | `/tmp/discord_import/tools/role-scraper/` |
| Tupperbox char definitions + avatars | Web dashboard (manual) | `https://tupperbox.app/dashboard/utilities` |
| Output raw (gitignored, `/tmp`) | — | `/tmp/discord_import/{raw,roles,tupperbox}/` |
| Output clean (gitignored, repo) | parser custom | `datasets/discord_yokai/` |

---

## Prerequisiti operator

### 1. Discord user token

Discord web (`https://discord.com/app`) → F12 DevTools → Network tab → click qualsiasi richiesta (es. `science`) → Headers → `authorization` → copia valore.

- NO virgolette, NO prefisso `Bearer`
- Stringa lunga ~70+ char
- Incolla in `.env`: `DISCORD_USER_TOKEN=...`

WARNING: token = accesso pieno al tuo account. `.env` è chmod 600 + gitignored. Non condividere.

### 2. Guild ID + Channel ID

Discord client → Settings (rotella) → Advanced → enable **Developer Mode**.

- Server icon → right-click → **Copy Server ID** → `KOY_GUILD_ID` in `.env`
- Channel "character-sheets" → right-click → **Copy Channel ID** → `CHARACTER_LIST_CHANNEL_ID` in `.env`

### 3. Tupperbox export (manual)

Sito ufficiale: `https://tupperbox.app/dashboard/utilities`

- Login con Discord
- **Import/Export** → bottone Export → scarica `.json` (tutti i tuppers)
- **Avatar Downloader** → scarica `.zip` (avatars full-res)
- Salva entrambi in `/tmp/discord_import/tupperbox/`

NOTE: Tupperbox dashboard mostra SOLO i tuoi tuppers (Horo/operator). Tuppers di altri giocatori non accessibili — verranno ricostruiti dal channel character-sheets.

---

## Esecuzione (dopo che .env è popolato)

### Fase A — DCE exportguild (messaggi + threads)

```bash
cd /tmp/discord_import/raw && set -a && source /home/nic/Scrivania/Quill_of_Calliope/.env && set +a && \
  ~/.local/bin/dce exportguild \
    -t "$DISCORD_USER_TOKEN" \
    -g "$KOY_GUILD_ID" \
    -f Json \
    --include-threads All \
    --media \
    --utc \
    -o "/tmp/discord_import/raw/" \
    --fuck-russia
```

Output: 1 JSON file per channel (incluso threads). Avatars + attachments in `_Files/`.

Stima: server 3 anni storia + ~50 channel ≈ 30-90 min, rate-limited.

### Fase B — discord-role-scraper

```bash
cd /tmp/discord_import/tools/role-scraper && \
  pip install -r requirements.txt && \
  python3 main.py "$DISCORD_USER_TOKEN" "$KOY_GUILD_ID" 1
```

Output: JSON in `export/` con roles, members, permissions, channel overwrites.

### Fase C — Tupperbox import

Manuale dashboard (vedi Prerequisiti §3). Output atteso in `/tmp/discord_import/tupperbox/`.

### Fase D — Parser → datasets clean

```bash
cd /home/nic/Scrivania/Quill_of_Calliope && \
  python3 scripts/import_discord_history.py \
    --raw /tmp/discord_import/raw/ \
    --roles /tmp/discord_import/roles/ \
    --tupperbox /tmp/discord_import/tupperbox/ \
    --out datasets/discord_yokai/
```

Output:
- `datasets/discord_yokai/messages_clean.jsonl` — tutti i msg normalizzati, IC/OOC/system tagged, Tupperbox proxy detected
- `datasets/discord_yokai/characters_discovered.jsonl` — char ricostruiti da character-sheets channel + Tupperbox webhook names
- `datasets/discord_yokai/players.jsonl` — mapping player_id → display_name → roles → tupper_names
- `datasets/discord_yokai/channels.jsonl` — metadata channel + topic + parent_category

---

## Sicurezza / TOS

- Discord user token scraping è grey-area TOS. Rischio ban basso per single export account-owned, ma esiste.
- Mitigation: rate-limit rispettato (`--respect-rate-limits True` default DCE). NO loops, NO automation continua.
- Tupperbox dashboard: 100% legittimo (è il tool ufficiale).
- Role-scraper: usa endpoint `/guilds/{id}/members-search` con fallback — rispetta rate limits.
