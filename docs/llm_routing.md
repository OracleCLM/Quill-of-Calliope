# LLM Routing — Quill of Calliope

**Operator-approved 2026-05-17 (via father-NM)**. Schema definitivo per M2/M3.

## Overview

Calliope routing tiers, basato su use-case + privacy hard boundary. Sensitive content (NSFW/violence/PII) → SOLO Ollama local, MAI cloud.

## Use-case → Tier matrix (OPERATOR-APPROVED)

| Use case | Tier | Model | Note |
|---|---|---|---|
| **Scene draft generation normale** | Cerebras | `qwen-3-235b-a22b` | Workhorse, batch-friendly |
| **Scene generation sensitive** (violence / sex / dark) | Ollama local | `dolphin-mistral-24b` (1st), `qwen-uncensored:32b` (fallback) | Privacy hard line, MAI cloud |
| **Climax scene rare max-quality** | Claude API (Max plan) | `claude-opus-4-7` | **Off-load via subprocess CLI** (NO API key consume — usa `claude` CLI Max session) |
| **Translation IT↔EN** (operator interface) | Groq | `llama-3.3-70b-versatile` | Fast, low latency |
| **Lore consistency check / retcon detection** | OpenRouter | `deepseek-r1-0528` | Deep reasoning |
| **Char voice mimicry top-5 chars** | Cerebras + LoRA future | TBD | LoRA training defer post-corpus (M4+) |

## Claude subprocess pattern (Climax tier)

`claude-opus-4-7` non chiamato via API key. Invece:
```bash
echo "<prompt>" | claude --model claude-opus-4-7 --print --output-format text 2>/dev/null
```
Sfrutta operator Claude Max plan, zero costo incremental, max quality.

## NSFW/violence/gore threshold scoring

Default conservative. Score per dimension 0-3:

| Dimension | Score | Action |
|---|---|---|
| `nudity_explicit` | 0=none, 1=implied, 2=partial, 3=full | ≥2 → Ollama local |
| `violence_gore` | 0=none, 1=mild, 2=graphic, 3=extreme | ≥2 → Ollama local |
| `non_consent` | 0=absent, 1=thematic, 2=implied, 3=depicted | ≥2 → Ollama local; 3 → block + log |
| `minors_adjacent` | 0=none, 1=ambiguous, 2=present, 3=involved | ≥2 → Ollama local; 3 → block + log |

**Hard rule**: qualsiasi dimension ≥2 → Ollama local OBBLIGATORIO. Score 3 in `non_consent` o `minors_adjacent` → block generation + log + alert operator.

## Privacy boundaries (ABSOLUTE)

- **Sensitive content** (any dim ≥2) → Ollama local ONLY
- **Player real names / PII** → MAI cloud
- **Character descriptions** (fictional persona) → cloud OK
- **Scene summaries** → cloud OK SE stripped di PII + sensitive context

Tutto outgoing a cloud deve essere anonimizzato. NO biometrics, contact info, real-world identifiers.

## Implementation

- Router: `route_scene(scene_type: str, nsfw_score: dict, char_relevance: str) -> tier_name`
- Config: `llm_routing_config.yaml` (operator-editable, validated on load)
- Override: CLI flag `--force-tier=<name>` bypassa auto-routing (operator-auth richiesto)
- Logging: ogni routing decision + override → audit log local
- Fallback: tier unavailable → downgrade safe (local preferred per sensitive)
- Model hot-swap Ollama via config; safety tiers richiedono operator confirm

## Cost model

| Tier | Costo per call | Quando usare |
|---|---|---|
| Cerebras | $0 (free tier operator) | Default per generation |
| Groq | $0 (free tier) | Fast Q&A, translation |
| OpenRouter | $0 (free tier qwen3) | Reasoning |
| Ollama local | $0 + compute time NM | OBBLIGATORIO sensitive |
| Claude Max subprocess | $0 incremental (Max plan paid già) | Rare climax only |
| Anthropic API key | $$$ | NON usare (subprocess pattern instead) |

## Implementation

**Script**: `scripts/route_scene.py` (M3 sprint #1, 2026-05-17)

```bash
# Basic routing decision
python scripts/route_scene.py --scene-type action_combat

# NSFW score override → forces Ollama local
python scripts/route_scene.py --scene-type action_combat \
  --nsfw-score '{"nudity_explicit":0,"violence_gore":2,"non_consent":0,"minors_adjacent":0}'

# High char relevance → marks lora_candidate
python scripts/route_scene.py --scene-type lore_exposition --char-relevance high

# Library import
from route_scene import route_scene, BlockedContentError
result = route_scene("action_combat", {"violence_gore": 0, ...})
```

Config operator-editable: `data/llm_routing_config.yaml`.
Exit code 2 su `BlockedContentError` (cron-friendly).

## HTTP Bridge (M3)

FastAPI server che espone `_call_llm` via REST locale su `127.0.0.1:8766`.

**Architettura**:
```
route_scene.py → localhost:8766 → llm_gateway_http.py → MCP server _call_llm → provider API
```

**Start**:
```bash
bash scripts/start_llm_gateway_http.sh
# oppure con porta custom:
bash scripts/start_llm_gateway_http.sh --port 8766
```

**Endpoints**:

| Endpoint | Metodo | Uso |
|---|---|---|
| `/health` | GET | Status + lista provider attivi |
| `/llm_ask` | POST | Q&A rapide (default: groq) |
| `/llm_code` | POST | Codegen/reasoning pesante (default: cerebras) |

**Request body** (JSON):
```json
{
  "provider": "groq",
  "prompt": "...",
  "max_tokens": 1024,
  "temperature": 0.7
}
```

**Response**:
```json
{
  "content": "...",
  "provider": "groq",
  "model": "llama-3.3-70b-versatile"
}
```

PID file: `/tmp/calliope_llm_gateway.pid` — Log: `/tmp/calliope_llm_gateway.log`

## Versioning

- v1 (2026-05-17): operator-approved initial matrix
- v1.1 (2026-05-17): `scripts/route_scene.py` implementation + 11 test scenarios
- v1.2 (2026-05-17): `scripts/llm_gateway_http.py` HTTP bridge — porta 8766
- v2+ tuning via M3 CLI tutor `calliope llm-tier-tune` (TBD)
