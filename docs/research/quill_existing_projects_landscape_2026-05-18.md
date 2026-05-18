---
title: Quill of Calliope — Existing Projects Landscape (Light Scan)
date: 2026-05-18
sprint: R-QUILL-LITERATURE-RESEARCH-EXISTING-PROJECTS-LIGHT
scope: light scan, no heavy gap-mapping
sources: groq llama-3.3-70b (initial), Claude Opus 4.7 (verification + augmentation, training cutoff jan-2026)
---

# Existing Projects Landscape — Quill of Calliope

**Purpose**: Mappa awareness dei progetti esistenti nei 3 pillar di Quill (scene narrative pipeline + Live2D streaming companion + Discord/Twitch RP bots). NON gap-mapping prescrittivo — operator è soddisfatto della direzione corrente.

**Verification policy**: URL e stack confermati da training knowledge sono linkati. Item non verificabili → marker `[unverified]`. Meglio onesto che fabbricato.

---

## Pillar 1 — Scene Narrative Pipeline / Storytelling AI

LLM-driven scene generation, character sheet management, lore retrieval, RP context persistence.

| Project | Purpose | Stack | URL | Relevance |
|---|---|---|---|---|
| **SillyTavern** | Frontend per LLM chat con character cards, lorebook, world-info, group chat, extras (TTS/STT/Stable Diffusion) | Node.js + vanilla JS + Express | github.com/SillyTavern/SillyTavern | **High** |
| **Oobabooga text-generation-webui** | LLM inference UI con extension layer (Discord, TTS, character chat) | Python + Gradio | github.com/oobabooga/text-generation-webui | High |
| **Risu AI** | Character chat frontend, alternativa a SillyTavern, focus UX + multi-modal | TypeScript + Svelte (web/Tauri) | github.com/kwaroran/RisuAI | High |
| **Agnaistic (Agnai)** | Multiplayer character chat, group RP, hostable + SaaS | TypeScript + Node.js + React | github.com/agnaistic/agnai | High |
| **KoboldCpp** | LLM inference backend (GGUF), spesso usato come engine da frontend ST/Risu | C++ + Python wrapper | github.com/LostRuins/koboldcpp | Med (backend) |
| **Mikupad** | Frontend LLM minimalista single-file HTML, focus completion/story-writing | Vanilla JS single-page | github.com/lmg-anon/mikupad | Med |
| **Pygmalion ecosystem** | Suite character-tuned LLM + tooling community | Python + HF transformers | github.com/PygmalionAI | Med |

### Key takeaways Pillar 1
- **SillyTavern è de-facto standard** nella community RP/character-chat 2024-2026 — chiunque costruisca in questo spazio deve almeno comparare workflow e formato character card v2/v3 (PNG embed).
- Pattern comune: frontend chat-UI generica + backend LLM intercambiabile (OpenAI-compat API). Tutti supportano lorebook/world-info come RAG manuale (no embeddings).
- **Quill diverge** su: (a) ChromaDB embeddings invece di keyword lorebook, (b) scene-running cross-channel statefulness (non solo chat lineare), (c) workflow CLI-skill orientato a operator power-user singolo (non multi-user SaaS).

---

## Pillar 2 — Live2D / 2D Avatar Streaming Companions

AI-driven mascot/vtuber con TTS lip-sync, browser overlay per OBS, character animation reattiva.

| Project | Purpose | Stack | URL | Relevance |
|---|---|---|---|---|
| **pixi-live2d-display** | Libreria browser per rendere Live2D Cubism in PIXI.js, supporta lipsync via audio analysis | TypeScript + PIXI.js | github.com/guansss/pixi-live2d-display | **High** (Quill `shared/live2d_mascot/` usa questo stack) |
| **OpenSeeFace** | Face tracking open-source per webcam → blendshape stream (alternativa a iPhone TrueDepth) | Python + ONNX | github.com/emilianavt/OpenSeeFace | Med (input tracking, ortogonale a AI-driven) |
| **VTube Studio** | App Live2D streaming closed-source ma con API pubblica WebSocket | C# / Unity (closed app) | denchisoft.com (API examples: github.com/DenchiSoft/VTubeStudio) | Med (API integration possibile) |
| **VSeeFace** | App vtubing closed-source freeware (3D VRM, non Live2D) | Unity (closed) | vseeface.icu | Low (3D, fuori scope Live2D) |
| **Neuro-sama clones / "AI vtuber" community projects** | Tentativi community di replicare Neuro-sama (LLM + TTS + Live2D streaming) | Vari (Python/JS) | molti repo sparsi `[unverified]` — search GitHub "ai vtuber" | Med (concept-relevant) |
| **Live2D Cubism SDK** | SDK proprietario Live2D Inc. per integrare modelli — license free fino a $10M revenue/yr | C++/Unity/Web (closed source SDK) | live2d.com/en/sdk/ | Required (Quill uses) |

### Key takeaways Pillar 2
- **Live2D space è dominato da app closed-source** (VTube Studio, Animaze, VSeeFace) + SDK proprietario Live2D Inc. La nicchia open-source per browser rendering è coperta principalmente da `pixi-live2d-display`.
- **Neuro-sama (Vedal987)** è il riferimento culturale per "AI vtuber" ma il codice non è pubblico. La community ha vari cloni tentativi ma nessuno è arrivato a feature-parity ed è solidamente mantenuto.
- **Quill diverge** su: (a) browser-first overlay (non standalone app), (b) LLM-driven behavior con phoneme export per lipsync (vs audio-amplitude only), (c) tight integration con narrative pipeline (mascot reagisce a scene state, non solo TTS audio).

---

## Pillar 3 — Discord/Twitch Bots per RP / Character Voice

Multi-persona bot, AI-assisted GM, character voice consistency in chat.

| Project | Purpose | Stack | URL | Relevance |
|---|---|---|---|---|
| **Tupperbox** | Multi-persona Discord bot via webhook (proxy-rewrite messaggi user → character voice) | Node.js + Discord.js | github.com/tupperbox/tupperbox `[verify exact org]` | **High** (Quill ha import_tupperbox.py) |
| **PluralKit** | Plural-system Discord bot (origin: DID/plural community, riusato per RP) | C# .NET + PostgreSQL | github.com/PluralKit/PluralKit | High |
| **Avrae** | D&D 5e dice bot + character sheet manager per Discord | Python + discord.py | github.com/avrae/avrae | Med (TTRPG focus, non narrative-AI) |
| **SillyTavern Discord extras** | Plugin SillyTavern che esporta chat in Discord channel | Python (extras) | parte di `github.com/SillyTavern/SillyTavern-Extras` | Med |
| **Oobabooga Discord plugin** | Bot Discord che usa text-generation-webui come backend | Python | extension di text-generation-webui | Med |
| **Streamer.bot** | Twitch automation closed-source freeware (chat triggers → OBS/audio actions) | C# (closed) | streamer.bot | Med (Twitch-side automation) |
| **OBS Studio** | Streaming engine OSS, supporta browser source per overlay | C++ + Qt | github.com/obsproject/obs-studio | Required (Quill targets OBS overlay) |

### Key takeaways Pillar 3
- **Tupperbox/PluralKit pattern** = webhook-based message rewrite è lo standard de-facto per multi-persona in Discord. Quill già consuma export Tupperbox (vedi `scripts/import_tupperbox.py`) → allineamento.
- **Avrae** è il riferimento per TTRPG-mechanics in Discord ma è D&D-specifico e non integra LLM narrative — gap che Quill potrebbe colmare per system-agnostic RP.
- **Twitch side è più sparso**: nessun progetto OSS combinà chat-driven narrative AI + character voice in modo solido. Streamer.bot copre l'automation generica ma non LLM-aware.

---

## Convergence Opportunities — Differentiation Thesis

Punti dove la combo tri-pillar di Quill (narrative + Live2D + stream-bot) è **rara o assente** nei progetti esistenti:

- **End-to-end pipeline scene → mascot reaction → chat output**: Nessun progetto FOSS noto chiude il loop "LLM scene generated → Live2D pose/expression cambia → Discord/Twitch chat riceve narration in character voice" come unified workflow. SillyTavern + VTube Studio + un bot separato richiederebbero glue manuale; Quill lo integra nativamente.

- **Local-first privacy con ChromaDB lore RAG**: La maggior parte dei progetti narrative usa lorebook keyword-based (ST world-info) o cloud RAG (OpenAI Assistants). Quill embedding-based + 100% locale è una posizione rara — privacy-sensitive operator (RP intimate/mature) non ha buone alternative FOSS.

- **CLI-skill operator-power-user UX**: SillyTavern/Risu sono GUI-first. Quill è CLI+skill-orchestrator first (tmux pane, MCP routing, slash skills) — design choice rara nello spazio RP, condivisa più con il mondo dev-tools (Claude Code, Aider) che con i frontend RP tradizionali.

- **Multi-tier LLM routing (Cerebras/Groq/OpenRouter/Ollama/Claude)**: Frontend tipici usano un singolo provider configurato. Quill routing per task-type (draft/translate/reasoning/uncensored/climax) è pattern enterprise/dev mai visto applicato a RP narrative — token-economy nativa nel workflow creativo.

---

## Notes & Caveats

- **Verification level**: voci marcate `[unverified]` o `[verify exact org]` richiederebbero check manuale (WebSearch o repo browsing) prima di citarle in documenti pubblici. Per landscape awareness interno sono OK.
- **Out of scope**: AI-Dungeon, NovelAI, CharacterAI, JanitorAI = SaaS commerciali closed, non comparable a Quill (local-first).
- **Discarded fabrications dal first-pass groq**: "CharacterSheetManager", "Lorekeeper", "OpenVTube", "AI-Character-Bot", "Twitch-Overlay-Bot", "Discord-RP-Bot" — nomi generici che il modello probabilmente ha inventato (nessuna corrispondenza nota in training knowledge). Esclusi.
- **Next research depth**: se operator vorrà heavy gap-mapping in futuro, partire da SillyTavern feature-matrix + Tupperbox webhook protocol + pixi-live2d-display API surface come ground-truth tecnico.
