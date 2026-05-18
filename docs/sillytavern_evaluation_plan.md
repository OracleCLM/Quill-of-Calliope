# SillyTavern Evaluation Plan (Path C hybrid)

> Setup + test rapido SillyTavern come foundation Calliope.AI. 1 giorno effort. Decision data-driven post-eval.

## Status

PLAN draft 2026-05-16. Setup execution: M0 night (questa notte) o post-operator-wake.

## Setup steps

### Step 1 — Prerequisites check (VERIFIED 2026-05-16)

✅ Node.js v24.12.0 (>=18 required, OK)
✅ npm 11.6.2
✅ git 2.43.0
✅ Disk 80GB free su 458GB

Pre-requisites COMPLETI. Setup pronto a partire.

```bash
# Per ricordare:
node --version  # SillyTavern needs Node.js 18+
npm --version
git --version
```

### Step 2 — Clone SillyTavern
```bash
cd ~/Scrivania
git clone https://github.com/SillyTavern/SillyTavern.git
cd SillyTavern
git checkout release  # stable branch
```

### Step 3 — Install dependencies
```bash
npm install
```

Note: ~500MB node_modules, può richiedere 5-10min.

### Step 4 — First launch
```bash
./start.sh  # Linux
# OR: node server.js
# Opens browser http://localhost:8000
```

Listening port default: 8000. CONFLICT con Workspace clmforecast.api → cambia config a 8002 o altro.

### Step 5 — Configure LLM backends
Web UI → Settings (gear icon top-right):

1. **Claude API** (Anthropic):
   - Type: Chat Completion
   - Source: Claude (Anthropic)
   - API key: copia da `~/.config/anthropic/api_key` o env
   - Model: claude-opus-4-7
   - Use OAS prompts: Yes

2. **Ollama local**:
   - Type: Text Completion
   - Source: Custom (compatible with OpenAI)
   - API URL: `http://localhost:11434/v1`
   - Model: `dolphin-mistral:7b` (per scene sensibili)

3. **Cerebras MCP** (via OpenAI-compatible proxy):
   - Type: Chat Completion
   - Source: OpenAI custom
   - API URL: TBD (Cerebras endpoint diretto via env `CEREBRAS_API_KEY`)
   - Model: `qwen-3-235b-a22b-instruct-2507`

### Step 6 — Test character card import
```bash
# Cerca community character cards Yokai-themed
# Example: github.com/AICharCards/ collection
# OR: crea PNG card manualmente con base TavernAI editor
```

Test session:
- Importa 1 char card (PNG con embedded JSON metadata)
- Crea 1 persona (operator profile narrativo)
- Crea 1 World Info entry (lore Yokai folklore basic)
- Test conversation 5-10 turns
- Valuta quality output

## Evaluation criteria

| Criterio | Peso | Note |
|---------|------|------|
| Quality literate output | 30% | Vs Claude API standalone vs Cerebras MCP standalone |
| Persistence cross-session | 20% | Char + lore + persona memoria |
| Workflow operator-friendly | 20% | UI intuitiva, char swap rapido, scene switching |
| Multi-LLM routing | 15% | Switch easy Claude/Ollama/Cerebras per scena |
| Customization extensibility | 10% | Extensions API per nostro Discord integration future |
| Local-only privacy | 5% | NO telemetry, NO cloud sync default |

## Decision matrix Path C

### Path C1 — SillyTavern + minimal custom layer
SillyTavern come UI primaria + Calliope skills come MCP custom endpoints + Atlante-style ChromaDB shard separata.

PRO: 80% del lavoro già fatto, vasta community, extensions readymade
CONTRO: tight UI coupling, harder Discord integration

### Path C2 — SillyTavern come reference, Calliope custom full
Studio SillyTavern features + replicare quelle utili nostro CLI Atlante-style. Niente SillyTavern in production.

PRO: full control, integration nativa Atlante stack
CONTRO: 3-4 settimane dev

### Path C3 — Hybrid switch
SillyTavern per scene quick-RP standalone. Calliope CLI per workflow strutturato (import Excel, scene tracking lungo, lore consistency). Operator switche tra i due via use-case.

PRO: best of both
CONTRO: maintenance 2 toolchain, context split

## Raccomandazione preliminare

**C3 hybrid switch** se SillyTavern post-eval impressiona per quality output. **C2 custom** se SillyTavern UI è ingombrante o non si integra bene con MCP.

Decision deferred a post-eval con operator review.

## Next steps esecuzione

1. (Stanotte autonomy) Clone + install SillyTavern (~30min download + npm install)
2. (Stanotte autonomy) First launch + screenshot UI per docs
3. (Stanotte autonomy) Test character card sample import
4. (Operator wake-up) Review screenshots + evaluation results → decide Path C1/C2/C3
5. (Post-decision) Sprint M2-prep dispatch sonnet-cops

## Status: PLAN ready, esecuzione next
