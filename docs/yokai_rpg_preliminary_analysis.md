# Yokai RPG — Excel preliminary analysis (2026-05-16 notte)

> Analysis automated del file `Yokai.xlsx` operator-provided. Findings strutturali + dataset metrics + import strategy refinement.

**Source file**: `~/Scrivania/Documenti/RP/Yokai RPG/Yokai.xlsx` (3.2MB)
**Copy safe**: `/tmp/calliope_import/Yokai.xlsx` (intoccato originale)
**Analysis date**: 2026-05-16 06:00 CEST
**Tool**: pandas + openpyxl + html.unescape

## Schema Excel (good news: PIÙ PULITO di quanto previsto)

| Column | Type | Use |
|--------|------|-----|
| `message` | str | Content (HTML entities encoded — `&#39;` = `'` ecc) |
| `player` | str | Discord username (es. "Horo" = operator) |
| `character` | str \| NaN | NaN = OOC, NOT NaN = IC |
| `timestamp` | datetime | UTC timestamp |
| `original message` | str \| NaN | Pre-edit content? (da chiarire con operator) |
| `system message` | str \| NaN | Tupperbot/Discord system messages |

**Filtering automatic**:
- IC messages: `character` NOT NaN → 16,769 rows (51.4%)
- OOC messages: `character` NaN + `player` NOT NaN → 15,829 rows (48.6%)
- System: `system message` NOT NaN → 256 rows

**HTML entities mandatory decoding**: messages contain `&#39;` (apostrophe), `&amp;`, ecc. Pre-import: `html.unescape(str(msg))`.

## Dataset metrics

- **Total messages**: 32,598
- **Timeline**: 1110 giorni (Nov 2021 → Nov 2024)
- **Storage**: 3.2MB raw → stima ~5MB JSONL parsed → ChromaDB index ~50-100MB embeddings

## Players ranking (top 10)

| Rank | Player | Messages |
|------|--------|----------|
| 1 | **Horo** (operator) | 12,608 (38.7%) |
| 2 | LittlePinkRin | 3,764 (11.5%) |
| 3 | 𝕋𝕖𝕞𝕡𝕖𝕤𝕥 | 2,599 (8.0%) |
| 4 | RaphaelFurious | 2,481 (7.6%) |
| 5 | Neji/Hans | 1,415 (4.3%) |
| 6 | Just frog | 1,369 (4.2%) |
| 7 | Katie | 1,193 (3.7%) |
| 8 | Joshua Thudson | 770 (2.4%) |
| 9 | YourGoblinBard | 700 (2.1%) |
| 10 | Solriise (Hiatus) | 548 (1.7%) |

**Operator = "Horo"** — username operator nel server. Filter critical: `df['player'] == 'Horo'` per estrarre tutto operator content per training/style analysis.

## Characters ranking (top 20)

| Rank | Character | Messages | Player owner |
|------|-----------|----------|--------------|
| 1 | **NARRATOR** | 1,743 | Horo (operator GM persona) |
| 2 | **Aurora** | 655 | Horo (queen primary char) |
| 3 | Philip Annabelle | 610 | RaphaelFurious |
| 4 | Koibo | 465 | (TBD) |
| 5 | Cassandra Blythe | 434 | (TBD) |
| 6 | Mirko | 372 | (TBD) |
| 7 | Saturn | 362 | (TBD) |
| 8 | Pdor | 326 | (TBD) |
| 9 | Peaches | 325 | (TBD) |
| 10 | Arianna | 323 | (TBD) |
| ... | ... | ... | ... |

**Operator chars detected** (player=Horo + filtered):
- NARRATOR (1743) — GM voice
- Aurora (655) — queen Holo-inspired primary
- Più altri char (Horo gestisce sicuramente più PC/NPC)

## Operator style identified (sample analysis)

### NARRATOR style (Horo)
> "A mix of horrified gasps and anxious laughter rose from the crowd..."
- Third-person omniscient scene-setting
- Sensory details (gasps, laughter, crowd mood)
- Sentence rhythm flowing

### Aurora style (Horo)
> "*Aurora beamed silently with excitement when Peaches responded eagerly, ears twitching with delight. She pressed her cheek slightly against Peaches' lips to "seal" the kiss, as if savoring it.*  Wonde..."
- `*action italic*` markers (operator emphasis pattern)
- Sensory micro-details (ears twitching, cheek pressing)
- Emotional layering ("excitement... delight... savoring")
- Holo Spice and Wolf inspired: animal traits (ears) + sensual playfulness

### Pattern marker comparison (other players)
- Horo: `*action*` asterisk italic
- RaphaelFurious: `_thought_` underscore italic (different pattern)
- Implication: punctuation/markdown signature varia per player

## Import strategy refined (M1)

Step 1 — **Load + decode HTML entities**:
```python
import pandas as pd, html
df = pd.read_excel('Yokai.xlsx', engine='openpyxl')
df['message_clean'] = df['message'].apply(lambda x: html.unescape(str(x)) if pd.notna(x) else None)
```

Step 2 — **Split IC/OOC/System**:
```python
ic = df[df['character'].notna()].copy()
ooc = df[df['character'].isna() & df['player'].notna()].copy()
system = df[df['system message'].notna()].copy()
```

Step 3 — **Operator-specific extraction**:
```python
operator_ic = ic[ic['player'] == 'Horo'].copy()  # ~2400 messaggi stima (NARRATOR + Aurora + altri)
operator_style_corpus = operator_ic['message_clean'].tolist()
# Save to scripts/training_data/operator_style.jsonl per future LoRA training
```

Step 4 — **Char extraction batch (MCP cerebras)**:
Per ogni char top-20, MCP cerebras analizza ~30-50 messaggi sample:
- Speech pattern (formal/informal, vocabulary, sentence length)
- Behavior pattern (action types, decision style)
- Output: `characters/<char_id>.draft.yaml` per operator review+approve

Step 5 — **Scene tracking heuristic**:
- Temporal cluster: messaggi within 30min window = stessa scene
- Char overlap: stessi player+char attivi = stessa scene continuation
- Output: `scenes/scene_<auto_id>.yaml` con participants + first/last timestamp + summary

Step 6 — **ChromaDB index 3 collections**:
- `calliope_characters` — embed da char_sheets.draft.yaml
- `calliope_messages` — embed da operator_ic + recent ic (last 6 mesi)
- `calliope_scenes` — embed da scene auto-detected

## Next steps (per operator approve)

1. **Operator review schema findings** (questa doc + char list)
2. **Approve operator-style extraction** (corpus Horo per fine-tune future)
3. **Approve char extraction batch** (MCP cerebras genera draft char_sheets per top-20)
4. **Approve scene auto-tracking** (heuristic temporal+overlap)
5. **Approve ChromaDB indexing** (~50-100MB embeddings local)

Esecuzione completa M1 IMPORT (Steps 1-6): ~6-8h dispatch sonnet-cops + MCP cerebras.

## Sample size budget M1

- Operator history (Horo): 12,608 msgs full
- Top char history (per top 10 char): ~500 msg each = 5,000 total
- Lore extraction: NARRATOR messages (1,743) → world-building extract
- Recent dynamics: last 6 months messages all players (~3-5,000 msgs)
- **Total embeddable**: ~25,000 messages = ~500K-1M tokens embeddings

**Cost embeddings**: nomic-embed-text local Ollama free. **Time**: ~30-60min indexing su NM CPU.

## Anti-pattern findings (lessons)

1. **NO assume Excel is chaotic** — operator preoccupazione era "mescolato" ma in realtà schema separato bene (51% IC clean filter)
2. **NO ignore HTML entities** — `&#39;` ecc rotture display se non decoded
3. **NO conflate `player` con `character`** — un player gestisce N character + OOC voice
4. **NO dimenticare NARRATOR**: operator GM voice è canonical lore source, deve essere indexed separato per scene narration coherence

## Operator-decision required pre-M1 dispatch

(D1) Filter char per import: TOP 20 (above) OR ALL ~200 char unique (più dati → più char sheets ma più rumore)?

(D2) Operator-style corpus extraction: SOLO IC Horo (12,608) OR also OOC Horo (meta-comments game design preferences)?

(D3) Time range index: TUTTO 3 anni OR solo last 6 mesi (~5K msg recent dynamics)?

(D4) Scene auto-tracking: GENERATE draft scenes auto OR operator-controlled scene declaration?

(D5) Char relationships extraction: dedurre da co-occurrence frequency OR lascia operator declare in char sheets manualmente?

Mattina rispondi e dispatch M1 IMPORT script execution.
