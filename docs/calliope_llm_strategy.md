# Quill of Calliope — LLM strategy 4-tier + OBLITERATUS plan

> Token-conscious routing. MCP-first rigoroso (operator-mandate). Claude API SOLO scene climax critical.

## Tier 1 — Cerebras qwen-3-235b (WORKHORSE)

**Use case**: drafts literate response + analysis text + character extraction + scene tracking

**Why**:
- Top model class instruction-tuned (235B params, multi-lingual ottimo italian/english)
- Cerebras inference SUPER fast (>1000 tok/s typical) → drafts in 5-10 secondi
- Free via MCP gateway (no $ per call)
- Quality vicino a Claude/GPT-4 per creative writing

**Invocation**:
```python
mcp__llm-gateway__llm_ask(
  provider="cerebras",
  model="qwen-3-235b-a22b-instruct-2507",
  prompt="...",
  temperature=0.7  # higher for creative
)
```

## Tier 2 — Groq llama-3.3-70b (TRANSLATION + Q&A)

**Use case**: italian → english fantasy translation + summarization + Q&A intermedi

**Why**:
- 70B params, well-tuned multi-lingual
- Groq inference fast (~500 tok/s)
- Free via MCP gateway
- Translation quality alta (mid-tier vs cerebras-235b)

**Invocation**:
```python
mcp__llm-gateway__llm_ask(
  provider="groq",
  model="llama-3.3-70b-versatile",
  prompt="Translate to English fantasy literate: ...",
  temperature=0.3  # lower for translation accuracy
)
```

## Tier 3 — OpenRouter deepseek-r1 (REASONING)

**Use case**: plot consistency check + lore coherence verification + complex narrative reasoning

**Why**:
- Reasoning-tuned, thinks step-by-step
- Catches inconsistencies cerebras-235b might miss
- Free via MCP gateway (deepseek-r1-0528)

**Invocation**:
```python
mcp__llm-gateway__llm_code(
  provider="openrouter",
  model="deepseek/deepseek-r1-0528",
  prompt="Check if draft is consistent with lore: ...",
  temperature=0.1
)
```

## Tier 4a — Ollama local UNCENSORED (SCENE SENSIBILI)

**Use case**: scene violente/erotiche/dark narrativamente giustificate

**Modelli candidati Ollama** (already available no abliteration):
- `dolphin-mistral:7b` — uncensored mistral baseline
- `dolphin-mixtral:8x7b` — uncensored mixtral, larger
- `nous-hermes2-mixtral:8x7b` — Nous Research uncensored
- `openhermes-2.5-mistral:7b` — Teknium uncensored

**Why local NOT MCP**:
- Sensibili = privacy-first, NO cloud transit
- Uncensored = ChatGPT/Claude refuse, Groq/Cerebras pure refuse
- Free, no rate limit

**Invocation**:
```python
mcp__ollama-tools__ollama_ask(
  model="dolphin-mixtral:8x7b",
  prompt="...",
  options={"temperature": 0.8}
)
```

**RAM cost**: dolphin-mixtral 26GB Q4_K_M (entra su NM 15GB? Probabilmente swap → lento). Più realistic: `dolphin-mistral:7b` Q4 ~4GB OK su NM.

## Tier 4b — OBLITERATUS abliterated top models (FUTURE P2)

**Use case**: scene sensibili HIGH-QUALITY (post-evaluation tier 4a non basta)

**Tool**: `~/Scrivania/OBLITERATUS/` (Pliny the Prompter abliteration). Mechanistic interpretability per remove refusal direction da activation space → keep brain.

**Top candidati censored da abliteration**:
- Qwen-2.5-72B-Instruct (~40GB Q4) → abliterated Qwen-2.5-72B-uncensored
- Llama-3.3-70B-Instruct (~40GB Q4) → abliterated Llama-3.3-70B-uncensored
- Mistral-Large-2411 (~70GB Q4) → abliterated Mistral-Large-uncensored

**Cost abliteration**:
- One-time GPU run (8-16h H100 single, OR distributed CPU multi-day)
- Need GPU access (NM no GPU, SL RTX 4060 8GB insufficient per 70B abliteration train)
- Workaround: run abliteration su HuggingFace Spaces (free tier limited, paid $0.50-2/h)
- Output: model file uploadabile a Ollama via `ollama create`

**Quality**: abliteration retain ~95% original perf. 70B-abliterated >> 7B uncensored nativi.

**Status**: NOT MVP. P2 future quando Tier 4a non basta. Operator può iniziare con dolphin-mistral 7B, valutare quality, escalare a abliteration se serve.

## Tier 5 — Claude CLI standalone (NO API — operator-update 2026-05-16)

**Use case**: drafts critical literate + scene climax + lore consistency checks complessi

**Why this matters**:
- Operator usa Claude Code CLI con account Max plan (abbonamento mensile, NO API per-call cost)
- ZERO incremental $ per uso → posso usare Claude CLI PIÙ liberamente
- Quota Max plan share con cops/Atlante work (gestibile, ~3-5 long drafts/giorno = ~30K-100K token usage)
- Claude Opus 4.7 best quality literate prose disponibile

**Invocation pattern**:
```bash
# Spawn ad-hoc Claude session in dir Calliope con context
cd ~/Scrivania/Quill_of_Calliope
claude --model claude-opus-4-7 --dangerously-skip-permissions
# Poi nel prompt: load context da ChromaDB (skill pre-built)
# /skill calliope-load-scene-context <scene_id>
# /skill calliope-draft-response <intent_italiano>
```

OR via Calliope CLI wrapper:
```bash
calliope draft --tier claude --scene <id> --intent "<italiano>" 
# Wrapper spawns Claude session ephemeral, loads context, runs draft, returns output
```

**Anti-pattern**: usare Claude per OGNI draft. MCP-first resta default (cerebras workhorse). Claude only quando:
- Scene climax narrativamente importante (operator-flag)
- MCP output qualitativamente insufficiente (rare)
- Lore consistency check complex multi-doc

**Quota management**: Max plan has 5h rate limits. Monitor via Claude CLI status. Se vicino quota, fallback Tier 1-4.

## Routing decision tree (skill `calliope-draft-response`)

```
Scene context loaded → intent operator analyzed:

1. Sensitive content flag (violence/erotic/dark)?
   YES → Tier 4a (Ollama dolphin-mistral local)
        IF quality insufficient → Tier 4b abliterated (future)

2. Critical climax scene operator-flagged?
   YES → Tier 5 (Claude API)

3. Plot consistency check needed?
   YES → Tier 3 (OpenRouter deepseek-r1) post-draft

4. Default literate response?
   → Tier 1 (Cerebras qwen-3-235b)

5. Translation only italian→english?
   → Tier 2 (Groq llama-3.3-70b)
```

## Cost projection mensile (UPDATED 2026-05-16)

**Update**: operator usa Claude CLI con Max plan subscription (NO API). Quindi cost cash incrementale = $0.

Assumendo 10 drafts/giorno mix:
- 7 routine → Tier 1 (Cerebras free MCP) → $0
- 1 translation → Tier 2 (Groq free MCP) → $0
- 1 sensitive → Tier 4a (Ollama local free) → $0 (compute electricity ~$0.05)
- 1 climax → Tier 5 (Claude CLI Max plan) → $0 (incluso subscription)

**Total cash: $0/mese incrementale**. Compute cost electricity (~$1-2/mese stimato).

Vs ChatGPT Plus $20/mese → tutto incluso in Max plan esistente. Calliope si "appoggia" su quota già pagata.

**Quota consumption monitor**:
- Max plan ha 5h rate limits + weekly cap
- Calliope share quota con cops/Atlante work
- Stima share Calliope ~20-30% del weekly cap totale (3-5 long drafts/giorno × 30K token ognuno = 0.9-4.5M token settimanali)
- Operator può monitorare via Claude CLI `/status` per evitare burnout

## Future P3 idee LLM-related

- **Fine-tuning Ollama model con tuoi historical messages** (post-import Yokai Excel + ChatGPT history)
  - Output: personalized model che mimic tuo style literate exactly
  - Tool: Ollama Modelfile + LoRA fine-tune (Unsloth library, ~2-4h training su SL GPU)
  - Quality: better than Cerebras 235b generic se training data >1MB tuoi messaggi
- **Voice TTS** (Coqui XTTS-v2 local): drafts diventano audio, ascolti mentre cammini/cucini
- **Multi-agent NPC simulation**: ogni NPC un'istanza Ollama low-temp, simulate group dynamics autonomously per generate emergent storylines (advanced, expensive RAM)
