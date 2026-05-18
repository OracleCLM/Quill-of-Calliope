# Calliope.AI — Vision

> Musa della poesia epica. Assistente AI per narrazione e gestione di giochi di ruolo testuali, con focus letterario, persistenza del contesto, e privacy locale.

**Status**: 🟡 M0 SCAFFOLD (2026-05-16). Pianificazione completa, repo strutturato, MVP in progress.

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

- `calliope-draft-response` — main draft generator literate
- `calliope-translate-iten` — italiano fantasy → inglese fantasy vocab coerente
- `calliope-summarize-scene` — Discord thread → riassunto strutturato
- `calliope-lore-coherent` — scenario nuovo → suggerisce dettagli coerenti con lore esistente
- `calliope-character-action` — char + situazione → propone azioni in-character

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
- **ChromaDB shard separata**: `~/Scrivania/Calliope.AI/.chroma_calliope/`
- **.gitignore aggressivo**: datasets/ + .chroma_calliope/ + sessions/ + private chars
- **Skills no leak cross-project**: Calliope skills NON share data con Atlante / cops
- **NO pod** per ora (operator-mandate). SL future option SOLO se abliterated 70B+ serve.

---

## Repository structure

```
Calliope.AI/
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

- **M0 SCAFFOLD** (2026-05-16, DONE): repo struttura + VISION + .gitignore + manifest + 8 docs planning + 2 template + 1 stub script
- **M1 IMPORT** (target ~3-5 giorni): Excel/ChatGPT/Discord parsers + ChromaDB indexing + IC/OOC filter + scene tracking heuristic
- **M2 SKILLS CORE** (target ~5-7 giorni): 5 skill custom calliope-* (draft/translate/summarize/lore-coherent/character-action) + Vesta-Minerva persona/memory import
- **M3 CLI** (target ~7-10 giorni): TUI Textual commands base + ChromaDB query + scene long-tail revive
- **M4 SILLYTAVERN EVAL** (target ~10-14 giorni): integration test Path C consolidate vs full custom decision
- **M5 PRODUCTION + TTS + IMAGE GEN** (target ~3-4 settimane): workflow stable + TTS Piper (punteggiatura-aware + per-char voice) + Image gen (Vesta-Minerva reuse + ComfyUI IP-Adapter multi-char + SDXL anime/action + char LoRA training SL GPU)
- **M6 (futuro P3)**: Discord bot semi-auto + OBLITERATUS Tier 4b 70B abliterated + fine-tune LoRA con tuoi messaggi storici per voice replica perfetto

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
