# Quill of Calliope — Vision

> Musa della poesia epica. Assistente AI per narrazione e gestione di giochi di ruolo testuali, con focus letterario, persistenza del contesto, e privacy locale.

**Status**: 🟢 M0+M1+M2+M3.5+M4+Wave5+Sprint D+E+F+**M-A/B/C/D+GAP-13..35** (2026-06-18, ~22k LOC, 96 Flask routes). Redesign scene-chat COMPLETO (M-A: SSOT Card V2 + M-B: assembler-prompt+/api/write + M-C: split Lore UI + M-D: pannello-azioni contestuale). 847 test unit passano (1192+ totali, 2 failed pre-esistenti browser/e2e infra). Discord bot **codice pronto, attivazione operativa pending** (vedi M6). fix(GAP-26): position_order MAX+1 in /api/messages/next+/api/draft.

---

## 🟢 Scene-Chat (JanitorAI-style) — FOCUS ATTIVO, decisioni LOCKED 2026-06-16

> Feature-cardine corrente: la **scena = chat multi-personaggio stile JanitorAI**. Questa
> sezione **supera, per lo scene-chat, la foundation legacy SillyTavern** (vendor messo da
> parte). Grounding: `.planning/SCENE_CHAT_GAP_MAP_2026-06-16.md` + `.planning/VISION_SCENE_CHAT_DRAFT.md`.

**Obiettivo**: roleplay narrativo a scena-come-chat. nic scrive come **narratore** o **suoi
personaggi**; i messaggi degli **altri personaggi** sono **importati** dallo storico Discord
(scraping per-canale/data, **selezione manuale**); i modelli di scrittura producono testo di
**qualità** consultando contesto pertinente. Principio: **qualità narrativa > automazione cieca**.

**Decisioni LOCKED (nic 2026-06-16)**:
1. **Retrieval-mirato**: i modelli-scrittura (riassunto, generazione-su-indicazioni, traduzione,
   rifinitura) consultano **schede dei personaggi ATTIVI in scena + lore per key-match**
   (`triggered_entries()` base) iniettati nel prompt. NON meccanico-cieco, NON decisore-autonomo.
   Filtro-rilevanza-fine = evoluzione futura.
2. **Binding personaggio↔scheda = MANUALE** (definitivo; auto-binding Tupperbox→character_id
   **fuori scope**, inaffidabile).
3. **UI = MINIMALE-prima** (lista scene + compose narratore/personaggio + render-thread);
   **bolle + avatar JanitorAI-pieno = GOAL evolutivo** (non subito).
4. **Modello-scrittura = gateway cloud STRONG + UNCENSORED, configurabile** (qualità, NON cost-zero).
   ⚠️ **Cambio postura privacy** (operator-locked): l'hardware NM-portatile è insufficiente per un
   modello-forte locale (T500 2GB-VRAM, RAM satura) → la scrittura passa per un **gateway cloud
   configurabile**; **pod/SL-hosted resta opzione-privacy FUTURA**, non su questo portatile. Questo
   **supera** la postura legacy "local-only / NO-cloud / MCP-first" della VISION **per la scrittura
   scene-chat** (il resto della privacy locale — dati RP, ChromaDB — resta invariato).

**ESISTE (≈90% core)**: scraping Discord (`scripts/import_discord_history.py`), scraper-schede,
schema characters/sheets + lore-KB (`lore_kb.py`/`triggered_entries`), scene-as-chat backend
completo+verde (`/api/db/scenes*`, `scenes.js` base), LLM gateway (`plot_arc._groq_ask`).

**COSTRUITO (3 gap chiusi — 2026-06-18)**:
1. ✅ **Assistenza-scrittura con retrieval** (M-B + GAP-2): `prompt_assembler.assemble()` SSOT Card V2 + lore key-match + char_memory, budget adattivo per-modello. `content_enhanced` popolato dal pulsante "✦ raffina" (bolla) e dal pannello M-D (verbo Rifinisci). `POST /api/write` + `scene_refine.refine_message()` convergenti su stesso assembler.
2. ✅ **Binding manuale** (nessuna automazione — chiuso per decisione, confermato).
3. ✅ **UI chat JanitorAI minimal-first** (M-C + M-D): split Lore Personaggi/DB vs Eventi, pannello write-actions contestuale su selezione (genera/continua/rifinisci/traduci/riassumi/coerenza), compose narratore/personaggio, thread bubble con "Aggiorna bolla" in-place.

**Strategia-modello scrittura — SWITCH locale/cloud (nic 2026-06-16)**:
Il modello-scrittura è **configurabile** tra due backend, selezionabili via switch:
- **CLOUD** (default attuale): gateway **strong + uncensored**, **veloce**. Vedi decisione #4.
- **LOCALE** (opzione-privacy, ceiling DA TESTARE): modelli grossi **quantizzati**
  (**TurboQuant**) + **compressione KV-cache** + **caricamento layer-by-layer**. L'inferenza
  **lenta è ACCETTABILE** perché la scrittura RP **non è real-time**. Uncensored via
  **Obliteratus** (repo open in `~/Scrivania/Repo_open`) applicato ai modelli scaricati.
  RAM liberata **on-demand** chiudendo i processi non-necessari prima dell'inferenza.
  Onestà-hardware: NM-portatile **15GB-RAM / 2GB-VRAM** → locale **possibile ma lento/RAM-bound**;
  il **ceiling reale va testato** (quale taglia-modello regge). pod/SL-hosted = scaling futuro.

Piano-lavoro dettagliato: `.planning/SCENE_CHAT_WORKPLAN_2026-06-16.md`.

---

## Problema

Operatore conduce sessioni RP testuali fantasy/folklore (multi-anno, ~100 personaggi, <10 giocatori) su Discord. Pain-points:

1. **Context loss ChatGPT**: tool volatile, ri-incolla manuale ogni sessione, dimentica personaggi/lore/scene tra interazioni.
2. **Traduzione italiano → inglese literate**: operatore non-native, scrive in italiano per fluidità, traduce per qualità letteraria alta.
3. **Persistence cross-canale**: scene parallele in canali Discord diversi, char attivi in più scene contemporaneamente.
4. **Censura LLM**: ChatGPT rifiuta tematiche violente/erotiche/dark anche quando narrativamente giustificate.
5. **Time cost**: rispondere in modo "literate" richiede tempo prolungato per scrittura+revisione+traduzione.

---

## Soluzione (Path C hybrid — adopt + custom)

**Foundation**: SillyTavern (open source, RP-optimized UI, char cards + lore book + persona + multi-LLM) come base evaluation rapida.

**Custom layer**: skill + scripts + ChromaDB indexing + workflow CLI integrato con stack Atlante esistente (Python + Claude API + Ollama + Cerebras MCP).

**Privacy-first**: tutto NM locale. NO cloud upload dei dati RP. ChromaDB shard separata.

**MCP-First rigoroso** (operator-mandate token saving):
- Cerebras qwen-3-235b → drafts literate + analysis (workhorse)
- Groq llama-3.3-70b → translation Iten + summary + Q&A fast
- OpenRouter (deepseek-r1) → reasoning complex (plot, lore consistency)
- Ollama local → cheap brainstorming + uncensored sensibili (via OBLITERATUS abliteration)
- Claude API → SOLO scene climax critical (raro, $0.30/giorno target)

---

## Componenti core

### 1. Knowledge base persistente

- `characters/<nome>.yaml` — schede char (stats + backstory + traits + scene attive + speech patterns)
- `lore/<topic>.md` — geografia + fazioni + magic system + religioni + eventi storici
- `scenes/<id>.md` — running summary scene parallele (partecipanti + location + last reply)
- ChromaDB index → semantic search across all

### 2. CLI/TUI dedicata

Commands:
- `/draft scene-id` — genera draft response literate inglese da context scene + char + intent italiano
- `/char show <nome>` — mostra scheda + scene attive
- `/lore search <query>` — semantic search lore docs
- `/translate "<italiano>"` → English literate
- `/summarize <discord-paste>` — riassunto + key facts
- `/scene status <id>` — partecipanti + ultima reply + suggested next action

### 3. Skills custom (`~/.claude/skills/calliope-*`)

> **TECH-DEBT RESOLVED 2026-05-24**: skill CLI originariamente promesse come `~/.claude/skills/calliope-*` — decisione: **Flask-only** (opzione C). Tutte le funzionalità sono implementate come Flask routes, coerente con l'architettura Flask shell (Path C2). Nessuna skill CLI necessaria.

- `/api/draft` — ✅ draft literate da intent italiano + context scene/char/lore (Sprint D1)
- `/api/translate` — ✅ traduzione IT↔EN letteraria (M3.5)
- `/api/summarize` — ✅ summary strutturato + key_facts (Sprint D2)
- `/api/lore/check` — ✅ coerenza lore via ChromaDB + LLM review (Sprint D4)
- `/api/scene/revive` — ✅ risveglio scene dormienti con context completo (Sprint D3)

### 4. Discord integration GRADUALE

- **Fase 1 (MVP)**: NO bot. Copia-incolla resta, ma CLI prepara context smart (riduce friction ~70%)
- **Fase 2 (P2)**: Discord bot READ-ONLY importa canali → ChromaDB auto-index
- **Fase 3 (P3 ambitious)**: bot semi-auto propone reply come reaction su tuo messaggio, tu approvi/edit, posta

### 5. Import storico

- **Excel .xls Yokai RPG** (`~/Scrivania/Documenti/RP/Yokai RPG/Yokai.xls`):
  - Conversion `.xls → .xlsx` via libreoffice CLI headless
  - Parser pandas+openpyxl → JSONL
  - MCP cerebras: filtering OOC/IC/META automatico (parentesi/prefix/semantic)
  - MCP cerebras: scene tracking heuristics (temporal cluster + char overlap)
  - MCP cerebras: character extraction draft (speech pattern + actions)
- **ChatGPT export JSON** (Settings > Data Controls > Export):
  - Parser estrae user→assistant turns RP-related
  - MCP categorizza: brainstorming / translation / drafting / lore
  - Output: docs/rp_workflow_patterns.md con preferenze emergenti
- **Discord history** (DiscordChatExporter CLI):
  - Export channel-by-channel JSON
  - Indexabile ChromaDB
  - Char list export → import in SillyTavern

---

## LLM strategy 4-tier

| Tier | Provider | Modello | Use case | Cost |
|------|----------|---------|----------|------|
| 1 | Cerebras MCP | qwen-3-235b | Drafts literate + analysis | Free MCP |
| 2 | Groq MCP | llama-3.3-70b | Translation + summary + Q&A | Free MCP |
| 3 | OpenRouter MCP | deepseek-r1 | Reasoning complex | Free MCP |
| 4a | Ollama local | dolphin-mistral / abliterated | Scene sensibili uncensored | Free local |
| 4b | Claude API | claude-opus | Scene climax critical raro | $0.30/giorno target |

**OBLITERATUS integration** (futuro P2): top censored models (Qwen-2.5-72B / Llama-3.3-70B / Mistral-Large) → abliteration locale → uncensored alta-qualità per scene sensibili.

---

## Privacy

- **Local-only NM**: NO cloud upload dei dati RP (Discord/ChatGPT export inclusi)
- **ChromaDB shard separata**: `~/Scrivania/Quill_of_Calliope/.chroma_calliope/`
- **.gitignore aggressivo**: datasets/ + .chroma_calliope/ + sessions/ + private chars
- **Skills no leak cross-project**: Calliope skills NON share data con Atlante / cops
- **NO pod** per ora (operator-mandate). SL future option SOLO se abliterated 70B+ serve.

---

## Repository structure

```
Quill_of_Calliope/
├── README.md
├── VISION.md (questo file)
├── LICENSE (TBD: AGPL-3.0 coerente OBLITERATUS upstream o MIT più permissive)
├── .gitignore (aggressive: datasets/, .chroma/, sessions/, characters/private/)
├── .obsidian_kb.yaml (manifest vault paths se servono)
├── .claude/settings.json (hook hybrid override Calliope scope)
├── characters/           # char sheets YAML
├── lore/                 # lore docs Markdown
├── scenes/               # running scene summaries
├── scripts/              # import_excel + import_chatgpt + import_discord parsers
├── docs/                 # MVP_SCOPE + sillytavern_evaluation + workflow patterns
├── src/                  # CLI Python core + skills custom
├── tests/                # pytest unit + integration
├── datasets/
│   └── yokai_rpg/        # Excel converted + chunked + indexed (gitignored)
└── .planning/            # ongoing sprint tracking (gitignored)
```

---

## Roadmap milestone

- **M0 SCAFFOLD** (2026-05-16, ✅ DONE): repo struttura + VISION + .gitignore + manifest + 8 docs planning + 2 template + 1 stub script
- **M1 IMPORT** (✅ DONE): Excel/ChatGPT/Discord parsers + ChromaDB indexing + IC/OOC filter + scene tracking heuristic
- **M2 SKILLS CORE** (✅ DONE): tutte le funzionalità core implementate come Flask routes — draft, translate, summarize, lore-check, scene-revive. Tech-debt skill CLI risolto (Flask-only decision 2026-05-24)
- **M3 CLI Textual** (⛔ SOSTITUITO da M3.5): TUI Textual commands base originalmente pianificata — ABBANDONATA per Path C2 Flask shell
- **M3.5 FLASK SHELL** (✅ DONE — ANTICIPATO): Flask app operativa con route equivalenti CLI. Path C2 scelto vs TUI Textual originale
- **M4 WAVE5 + CONSOLIDATION** (✅ DONE): ~15.7k LOC, Wave5 feature batch completato
- **M5 LIVE2D + TTS** (✅ DONE — ANTICIPATO): Live2D integrato prima di schedule originale
- **M6 DISCORD BOT** (⚠ CODE READY — ACTIVATION PENDING): codice bot semi-auto presente (commit 297b10e, M4 feature), graceful-degradation widget UI Dashboard (Sprint B2). Attivazione in produzione pending operator-decision: (a) configurazione `CALLIOPE_DISCORD_BOT_TOKEN` in `.env`, (b) avvio processo via `scripts/start_discord_bot.sh`, (c) design separato "instructions + interpellation game master" che precede l'esposizione del bot ai canali live. Pattern coerente con principio "feature ready, activation pending".
- **Sprint D VISION GAP CLOSE** (✅ DONE 2026-05-24): /api/draft (D1), /api/summarize (D2), /api/scene/revive (D3), /api/lore/check (D4), VISION cleanup (D5). Tech-debt skill risolto.
- **NEXT: OPERATOR ACTIVATION** (pending): Discord bot activation M6 (operator-side: token + start script), scene revive UX polish (revival output panel refinement), lore docs manual enrichment (beyond auto-extracted)

**Componenti implementati non in VISION originale** (aggiunti post-brainstorm 2026-05-22):
- `plot_arc` — arco narrativo tracker
- `char_memory` — memoria persistente per personaggio
- `entity_linker` — entity disambiguation cross-scene
- `style_coach` — stile letterario consistency checker
- `twitch_bot` — integrazione Twitch (fuori scope originale, aggiunto)

## Scene long-tail persistence (DESIGN consideration 2026-05-16)

Operator-mandate: scene RP duraturanno settimane/mesi tipicamente. Design implications:

- **ChromaDB**: NO garbage-collect scene "dormant". Persistence forever-by-default.
- **Scene file**: `scenes/<id>.md` always preserved. `status: dormant` ≠ archived.
- **CLI command future**: `calliope scene revive <id>` per riprendere dopo lungo silenzio. Auto-load: scene file + char states + last 5 exchanges + related lore. Re-onboarding context per draft generation.
- **Reawakening notes**: ogni scene template ha sezione dedicated per "scene riprende dopo mesi". Operator può scrivere note "tema chiave + char states + last cliffhanger" durante dormancy per facilitare re-entry.
- **Time-in-world tracking**: messaggi possono indicare passaggio tempo in-world (es. "12 ore dopo nel village"). Scene template field `time_in_world_passed` aggiornabile.

---

## Anti-pattern (evitare da subito)

1. **NO fork SillyTavern**: usa upstream + custom extensions. Riduce maintenance burden.
2. **NO Claude API per task non-critical**: MCP-first rigoroso. Claude solo scene climax.
3. **NO commit dati RP**: gitignore aggressivo, char privati out of git.
4. **NO bot Discord diretto MVP**: copia-incolla resta workflow valido fino Fase 3.
5. **NO assumere lore consistency**: skill `calliope-lore-coherent` checka prima di publish draft.

---

## Refs

- [SillyTavern repo](https://github.com/SillyTavern/SillyTavern)
- [OBLITERATUS abliteration tool](~/Scrivania/OBLITERATUS)
- [DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter)
- Atlante enterprise prep: `~/Scrivania/Atlante/VISION.md` (pattern simile stack)
- Vesta-Minerva persona tracking: `~/Scrivania/Workspace/vesta_system1/`

---

**Operator**: nic (single user)
**Maintainer**: father-NM (opus orchestrator)
**Created**: 2026-05-16 brainstorming session post-Atlante enterprise prep

---

## Integrazioni candidate (stato: 2026-06-06)

| Integrazione | Stato | Note |
|---|---|---|
| **TurboQuant KV-cache** (Google Research ICLR 2026) | **WATCH** — ChromaDB/local | Se Calliope integra modelli locali per RAG narrativo o generazione, TurboQuant può ridurre OOM su sessioni lunghe; dipende da llama.cpp integration (non ancora disponibile) |
