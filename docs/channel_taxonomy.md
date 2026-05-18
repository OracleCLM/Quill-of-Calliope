# Channel Taxonomy — Quill of Calliope Discord ingestion

**Auto-decided 2026-05-17 (via father-NM)**. Heuristic classification rules. Operator override later via `channels_taxonomy.yaml` (empty OK for now).

## Channel types

| Type | Meaning | Retrieval default |
|---|---|---|
| `IC` | In-character narrazione (scene RP attive) | included |
| `OOC` | Out-of-character chat (operator/player meta) | excluded from scene-gen retrieval, included in training corpus |
| `meta` | Char sheets, rules, lore wiki, character-list | included (high signal) |
| `art` | Galleria immagini, fanart (low text content) | excluded by default |
| `admin` | Bot logs, mod actions | excluded always (no signal) |

## Heuristic classification rules

Applied in order, first match wins. Lowercase `channel.name` + `channel.parent_category`:

1. **`art`** if name OR parent contains: `art`, `gallery`, `fanart`, `images`, `pictures`
2. **`meta`** if name OR parent contains: `meta`, `rules`, `lore`, `wiki`, `sheet`, `character-list`, `characters-list`, `info`
3. **`OOC`** if name OR parent contains: `ooc`, `chat`, `off-topic`, `general`, `lounge`, `discussion`
4. **`admin`** if name OR parent contains: `bot`, `logs`, `mod`, `audit`, `staff`
5. **`IC`** default fallback (no match above)

## Operator override

File `channels_taxonomy.yaml` (gitignored):
```yaml
# Override heuristic classification per channel ID
overrides:
  "1316214929971220512": art         # forced (was IC by name)
  "1320529977732632697": meta         # characters-list (correctly heuristic-matched)
  "1493668378370506944": OOC          # "evil-plays-stuff" → OOC by override
```

Heuristic rules applicate PRIMA, override applicato DOPO (operator wins).

## Schema integration

Field `channel_type` aggiunto a `messages_clean.jsonl` (parser `import_discord_history.py` lo computa al parse-time):

```json
{
  "message_id": "...",
  "channel_id": "1320529977732632697",
  "channel_name": "characters-list",
  "channel_type": "meta",
  ...
}
```

ChromaDB metadata anche include `channel_type` per filter.

## Retrieval default per use-case

| Use-case | Channel types incluse |
|---|---|
| Scene generation | `IC`, `meta` |
| Training corpus | `IC`, `meta`, `OOC` |
| Lore consistency check | `meta`, `IC` |
| Translation context | tutti tranne `admin` |
| Char voice mimicry | `IC` only |

## Implementation note

Parser `import_discord_history.py` chiama funzione `classify_channel(name, parent) -> str`. Logica pure function, testabile, default classification documentata sopra. Override applicato dopo (load yaml if exists).

## Versioning

- v1 (2026-05-17): heuristic auto-decided. Operator override yaml vuoto.
- v2+ tuning quando operator playtest reveal misclassifications.
