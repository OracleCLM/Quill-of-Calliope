# Quill of Calliope — M4 Kickoff Plan

**Status**: PLANNING (sprint R-CALLIOPE-DAEMON-LAUNCHER-FIX-M4-KICKOFF, 2026-05-18)
**M3 baseline**: route_scene ✓ | narrative_state ✓ | TTS bilingual ✓ | Live2D Phase-2 ✓ | scene_narrative chain ✓

---

## M4 scope overview

| Component | Effort | Depends on | Priority |
|-----------|--------|------------|----------|
| Discord bot integration | M | scene_narrative, llm_gateway_http | P1 |
| Custom .moc3 mascot model | L-XL | Live2D frontend, operator decision | P2 |
| Twitch stream overlay | L | Live2D frontend, mascot_ws_server | P3 |
| Multi-mascot ensemble | XL | custom mascot, narrative_state | P4 |

**Recommended order**: Discord bot → custom mascot → Twitch → ensemble

---

## Component 1 — Discord Bot Integration

**Scope**: Bot listens to a designated Discord channel, routes messages to `scene_narrative.py`, posts generated scene reply.

### Dependencies (M3)
- `scripts/scene_narrative.py` — chain generation
- `scripts/llm_gateway_http.py` + `start_llm_gateway_http.sh` — LLM backend
- `scripts/route_scene.py` + `data/llm_routing_config.yaml` — tier routing
- `scripts/narrative_state.py` — per-channel persistent state

### Implementation path
1. `pip install discord.py` (or `nextcord`)
2. `scripts/calliope_discord_bot.py` — bot class + message handler
3. Message handler: parse `!scene <type> <text>` or freeform → `route_scene()` → `dispatch_to_tier()`
4. State: per-guild `narrative_state_{guild_id}.json`
5. Config: `.env` `DISCORD_BOT_TOKEN` (separate from user token used in M2)
6. Slash commands: `/scene`, `/state`, `/clear-state`

### Effort: M (5-8h)

### Blocker risks
- Discord bot token requires verified app in Discord Developer Portal
- Rate limits: 5 messages/5s per channel (implement cooldown)
- Long scene text (>2000 chars): Discord message limit → chunk/truncate

---

## Component 2 — Custom .moc3 Mascot Model

**Scope**: Replace Hiyori placeholder with operator-defined mascot (.moc3 Cubism 4 format).

### Operator decision required

| Option | Tradeoffs |
|--------|-----------|
| **Aurora of Winter** (Okami-mimi) | Familiar to operator, risk of canonical drift (Aurora is an RP char), requires artist commission or VRoid+Cubism |
| **Original "Calliope" mascot** | Clean slate, no lore conflict, higher commission effort |
| **CC0 VTuber model** (VRoid Hub) | Zero cost, fast setup (~2h), licensing risk if commercial |

**Recommendation**: Original Calliope design — avoid Aurora canon contamination. Decide at M4 kickoff session with operator.

### Implementation path
1. Commission or create .moc3 model (Cubism Editor 4.x)
2. Drop model into `frontend/live2d/models/calliope/`
3. Update `app.js` MODEL_URL → local path
4. Map expression slots (f00-f06) to 7-emotion library (already implemented in Phase-2)
5. Calibrate lip-sync parameters for new model

### Effort: L–XL
- VRoid + Cubism export: L (6-10h + artist time)
- CC0 model integration: S (2-3h)
- Custom commission: XL (artist timeline unknown)

### Blocker risks
- Model quality gate: pixi-live2d-display requires Cubism 4.x format
- Physics parameters (hair, clothing) need manual tuning in Cubism Editor
- Operator availability for design iteration

---

## Component 3 — Twitch Stream Overlay

**Scope**: Browser source overlay (OBS/Streamlabs) showing mascot + reacting to Twitch chat events.

### Dependencies (M3)
- `frontend/live2d/` — existing dashboard as browser source
- `scripts/mascot_ws_server.py` + `start_mascot_ws.sh` — state push
- `tts_speak.py` — TTS read-aloud for donations/raids

### Implementation path
1. `scripts/calliope_twitch_bot.py` — TMI.js or `twitchio` library
2. Event handlers: `on_message`, `on_subscribe`, `on_raid`
3. → Push state via WebSocket `:8767` → mascot reacts (talking/surprised/happy)
4. OBS browser source: `http://localhost:8080/frontend/live2d/` (transparent bg overlay)
5. CSS: `body { background: transparent !important; }` in stream mode

### Effort: L (8-12h)

### Blocker risks
- Twitch API OAuth: requires app registration + user auth token
- OBS browser source latency: ~100ms typical (acceptable)
- Audio capture: TTS via ALSA may not route through OBS — VirtualAudio solution needed

---

## Component 4 — Multi-Mascot Ensemble

**Scope**: 2+ mascots simultaneously on screen, independent state machines, dialogue between them.

### Dependencies
- Custom mascot (Component 2) for second character (e.g. Filomena)
- `narrative_state.py` — per-char state
- `scene_narrative.py` — dialogue chain gen
- Live2D Phase-3 (planned): Cubism SDK Web migration

### Implementation path
1. `app.js`: load N models from config, position side-by-side
2. `state_machine.js`: per-model state (`window.mascots = {aurora: {...}, filomena: {...}}`)
3. Dialogue: `scene_narrative.py --char-list "Aurora,Filomena"` → parse replies per-char → route to correct mascot TTS/expression
4. Lip-sync: two `TTSSync` instances, staggered to avoid overlap
5. Config: `data/mascot_ensemble_config.yaml` — model paths, positions, char-to-model mapping

### Effort: XL (20-30h)

### Blocker risks
- PIXI performance: 2× Live2D models → GPU-side (acceptable on NM with integrated GPU)
- Dialogue coherence: scene_narrative needs per-char reply parsing (new feature)
- TTS serialization: two audio streams must not overlap → queue required

---

## M4 milestone definition

**Done** when:
- [ ] Discord bot operational on at least 1 Yokai RPG channel
- [ ] Custom/replacement mascot loaded (any non-Hiyori model)
- [ ] Twitch overlay proof-of-concept (reaction to 1 event type)
- [ ] Multi-mascot: 2 models on screen simultaneously (no dialogue required)

**Not in M4 scope**: LoRA fine-tuning (M5), production CloudFlare/VPS deployment, mobile client.

---

## Effort summary

| Component | S | M | L | XL | Notes |
|-----------|---|---|---|----|-------|
| Discord bot | — | ✓ | — | — | 5-8h |
| Custom mascot | — | — | ✓→ | XL | depends on model path |
| Twitch overlay | — | — | ✓ | — | 8-12h |
| Multi-mascot | — | — | — | ✓ | 20-30h |
| **Total M4** | | | | | ~40-55h estimate |

---

## Reference: M3 deliverables building M4

| M3 output | M4 usage |
|-----------|---------|
| `route_scene.py` + 19 scene types | Discord/Twitch scene gen routing |
| `narrative_state.py` | Per-guild/per-stream persistent char state |
| `tts_speak_bilingual()` | Twitch TTS read-aloud events |
| `scene_narrative.py --state-file` | Discord bot context-aware replies |
| Live2D state machine + emotion transitions | Multi-mascot independent states |
| `llm_gateway_http.py` `:8766` | Discord/Twitch LLM backend |
| `mascot_ws_server.py` `:8767` | Twitch real-time state push |
