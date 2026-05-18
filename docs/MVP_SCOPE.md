# Calliope.AI — MVP scope (M1+M2+M3)

> Definizione strict del primo workflow funzionante operator-usable.

**Status**: draft 2026-05-16. Da validare con operator alla wake-up.

## Goal MVP

Operatore può:
1. **Importare** Excel storico Yokai RPG → ChromaDB index searchable
2. **Cercare** lore/char/scene tramite CLI semantic search
3. **Generare draft** literate inglese da intent italiano + context auto-loaded
4. **Tradurre** singole frasi italiano → inglese fantasy coerente
5. **Salvare** scene running summary cross-sessione

NO Discord bot (Fase 3). NO SillyTavern embed full (Fase 4). NO TTS (Fase 6).

## Schema dati

### Character sheet YAML

```yaml
# characters/<nome>.yaml
id: kazuki_takeda
name: Kazuki Takeda
alias: ["The Silent Blade", "Kazu"]
type: pc  # pc | npc | player_of_other
player: nic  # se pc
race: human
class: ronin
age: 28
backstory: |
  Nato in un villaggio sulle colline di Yamato...
traits:
  - taciturno
  - leale ad una fede dimenticata
  - skilled swordsman (katana)
speech_pattern:
  formal: true
  use_honorifics: true
  vocabulary: archaic_japanese_inflected_english
active_scenes:
  - scene_001_yamato_temple
  - scene_005_river_crossing
sample_quotes:
  - "The blade remembers what the heart forgets."
last_updated: 2026-05-16
```

### Lore Markdown

```markdown
<!-- lore/<topic>.md -->
---
topic: Yokai folklore — Kitsune
category: creatures
canonicity: established  # established | proposed | retconned
related: [yokai_general, fox_spirits, shapeshifting]
last_updated: 2026-05-16
---

# Kitsune — Spiriti volpe

Le kitsune sono yokai folkloristici giapponesi noti per...

## Tipologie
- Zenko (benigne, servitrici di Inari)
- Yako (selvagge, trickster)
...
```

### Scene running summary

```markdown
<!-- scenes/<scene_id>.md -->
---
scene_id: scene_005_river_crossing
location: Riva del fiume Tsubasa, alba
participants:
  - kazuki_takeda (nic)
  - emiko_yamashiro (other_player_alice)
  - npc_merchant_old
last_reply_at: 2026-05-15T22:30:00Z
status: active
mood: tense
---

## Running summary

Kazuki e Emiko incontrano un vecchio mercante sulla riva...

## Recent exchanges
[copia ultimi 5-10 messaggi rilevanti per context]

## Pending threads
- Kazuki deve rispondere alla domanda del mercante su un artefatto
- Emiko ha appena svelato un segreto del suo passato
```

## CLI commands (target M3)

```bash
calliope draft --scene scene_005_river_crossing --intent "Kazuki riflette sull'artefatto, poi risponde con cautela rivelando solo metà della verità"
calliope char show kazuki_takeda
calliope lore search "kitsune yako trickster"
calliope translate "Il vento sussurrava antichi nomi dimenticati"
calliope summarize --from-clipboard  # paste Discord scene → summary
calliope scene status scene_005_river_crossing
calliope import excel ~/Scrivania/Documenti/RP/Yokai\ RPG/Yokai.xls
calliope import chatgpt ~/Downloads/chatgpt-export.json
calliope import discord ~/Downloads/discord-channel-export.json
```

## Skills custom (target M2)

| Skill | Input | Output | LLM tier |
|-------|-------|--------|----------|
| `calliope-draft-response` | scene context + char + intent italiano | English literate draft 500-2000 char | Cerebras qwen-3-235b |
| `calliope-translate-iten` | text italiano | English fantasy vocab | Groq llama-3.3-70b |
| `calliope-summarize-scene` | long Discord thread paste | strutturato (location/participants/exchanges/threads) | Groq llama-3.3-70b |
| `calliope-lore-coherent` | scenario nuovo + lore docs | suggerimenti coerenti / inconsistency flags | OpenRouter deepseek-r1 |
| `calliope-character-action` | char yaml + situazione | proposte azioni in-character | Cerebras qwen-3-235b |

## ChromaDB schema

3 collection separate (semantic search granulare):

1. **calliope_characters** — embed da char_sheet.yaml (name + backstory + traits + speech_pattern + quotes)
2. **calliope_lore** — embed da lore/*.md (topic + body + related)
3. **calliope_scenes** — embed da scenes/*.md (location + participants + summary + recent_exchanges)

Embedder: ollama `nomic-embed-text` local (no API, no cost).

## Workflow tipico operatore (target)

1. Operator vuole rispondere a scena Discord
2. Copia ultimi messaggi scena da Discord → clipboard
3. `calliope summarize --from-clipboard` → riassume + identifica scene_id
4. `calliope draft --scene <id> --intent "<italiano>"` → genera draft inglese literate
5. Review/edit draft manuale (5-10% caso)
6. Copia-incolla su Discord
7. Operator scrive: `calliope scene update <id> --append-reply "<my reply>"` per persistence

Riduzione tempo stimata vs ChatGPT: 60-70% (no re-incolla context, no ri-spiegare char, draft direttamente literate).

## Anti-pattern (evitare M1+M2)

1. **Hardcode char/lore in skill prompts** — sempre via ChromaDB retrieve dynamic
2. **Claude API per ogni draft** — MCP-first rigoroso, Claude solo climax critical
3. **Fork SillyTavern** — usa upstream + custom extensions Path C
4. **Commit char private** — gitignore aggressivo (characters/private/, *.private.yaml)
5. **NO scene tracking automatico** — operator deve confermare scene_id, no auto-assign che può sbagliare

## Verify-real-completion criteria (per M1+M2+M3 closure)

- [ ] Excel Yokai.xls → ChromaDB indexed con scene_id assegnati + IC/OOC/META filtered
- [ ] 5 skill calliope-* in `~/.claude/skills/` con SKILL.md frontmatter
- [ ] CLI `calliope` invocabile + 7 commands functional + pytest unit basic
- [ ] Workflow E2E: importa Yokai.xls → search lore → draft scena reale → output literate inglese plausibile
- [ ] Token budget verificato: <$0.50/giorno medio (MCP-heavy)
- [ ] Privacy verify: NO file gitignored finiti committed (grep test)

## Next steps (post-MVP)

- M4: SillyTavern eval + Path C consolidation decision
- M5: production usable + char Discord list export → SillyTavern import
- M6: Discord bot semi-auto + TTS Coqui local
