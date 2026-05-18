# Dataset Schema — Quill of Calliope

Reference for all dataset output formats produced by the import pipeline.
Updated: 2026-05-17.

---

## 1. `messages_clean.jsonl`

**File:** `datasets/discord_yokai/messages_clean.jsonl`
**Source:** `scripts/import_discord_history.py`
**Format:** JSONL — one JSON object per line, UTF-8, no BOM.

| Field | Type | Description | Example |
|---|---|---|---|
| `message_id` | `str` | Discord snowflake ID of the message | `"1320593702623772756"` |
| `timestamp` | `str` | ISO 8601 creation timestamp (UTC) | `"2024-01-15T18:32:04.123+00:00"` |
| `timestamp_edited` | `str \| null` | ISO 8601 edit timestamp, null if never edited | `"2024-01-15T18:35:00.000+00:00"` |
| `channel_id` | `str` | Discord snowflake ID of the source channel | `"1312211590883442688"` |
| `channel_name` | `str` | Human-readable channel name | `"taverna-di-yorend"` |
| `parent_channel_id` | `str \| null` | Parent channel ID for threads; null for top-level channels | `"1312211590883442688"` |
| `guild_id` | `str` | Discord snowflake ID of the server | `"1312211590883442600"` |
| `author_id` | `str` | Discord snowflake ID of the message author | `"603341648360898581"` |
| `author_name` | `str` | Discord username of the author | `"yokai_gm"` |
| `author_nick` | `str \| null` | Server nickname; null if not set | `"The GM"` |
| `is_bot` | `bool` | True if the author is a bot account | `true` |
| `content` | `str` | Raw message text content | `"Alexis: Buonasera, cosa posso portarvi?"` |
| `msg_type` | `str` | DCE message type string | `"Default"` |
| `tag` | `str` | Classified tag: `IC`, `OOC`, or `system` | `"IC"` |
| `reply_to` | `str \| null` | `message_id` of the replied-to message; null if not a reply | `"1320593702623770000"` |
| `tupperbox_proxy` | `bool` | True if sent via Tupperbox proxy (bot + known tupper name) | `true` |
| `attachments` | `list` | List of attachment objects from DCE (may be empty) | `[]` |
| `reactions` | `list` | List of reaction objects from DCE (may be empty) | `[{"emoji": {"name": "❤️"}, "count": 3}]` |
| `player_status` | `str` | Enum: `member_current` / `former_member` / `unknown`. Popolato dopo merge con member list (default null). | `"member_current"` |

**Tag classification logic:**
- `system` — `msg_type` is `ThreadCreated` or `ChannelPinnedMessage`
- `OOC` — content (stripped) starts with `(` or `[`
- `IC` — all other messages

**Example record:**
```json
{
  "message_id": "1320593702623772756",
  "timestamp": "2024-01-15T18:32:04.123+00:00",
  "timestamp_edited": null,
  "channel_id": "1312211590883442688",
  "channel_name": "taverna-di-yorend",
  "parent_channel_id": null,
  "guild_id": "1312211590883442600",
  "author_id": "603341648360898581",
  "author_name": "Tupperbox",
  "author_nick": null,
  "is_bot": true,
  "content": "Alexis: Buonasera, cosa posso portarvi?",
  "msg_type": "Default",
  "tag": "IC",
  "reply_to": null,
  "tupperbox_proxy": true,
  "attachments": [],
  "reactions": []
}
```

---

## 2. `roles.jsonl`

**File:** `datasets/discord_yokai/roles.jsonl`
**Source:** `scripts/import_discord_roles.py`
**Format:** JSONL — one JSON object per line, UTF-8.
**Input:** Pipe-delimited markdown table exported from Discord.

| Field | Type | Description | Example |
|---|---|---|---|
| `name` | `str` | Role display name | `"GM"` |
| `id` | `str` | Discord snowflake ID of the role | `"1320593702623772756"` |
| `position` | `int` | Role hierarchy position (higher = more privileged) | `35` |
| `mentionable` | `bool` | True if the role can be @mentioned by members | `true` |
| `is_bot` | `bool` | True if the role's tags column contains "bot" | `false` |
| `permissions_flags` | `list[str]` | Active permission flag names (subset of 8 tracked flags) | `["administrator"]` |

**Tracked permission flags (in order):**
`administrator`, `mention all`, `manage guild`, `manage roles`, `manage channels`, `kick members`, `ban members`, `webhooks`

**Example record:**
```json
{
  "name": "GM",
  "id": "1320593702623772756",
  "position": 35,
  "mentionable": true,
  "is_bot": false,
  "permissions_flags": ["administrator"]
}
```

---

## 3. `players.jsonl` *(planned)*

**File:** `datasets/discord_yokai/players.jsonl`
**Status:** Not yet implemented — to be built by aggregating `messages_clean.jsonl` on `author_*` fields.

| Field | Type | Description | Example |
|---|---|---|---|
| `discord_id` | `str` | Discord snowflake ID (= `author_id`) | `"603341648360898581"` |
| `discord_name` | `str` | Most recent `author_name` seen | `"yokai_player1"` |
| `nick_history` | `list[str]` | All distinct `author_nick` values observed | `["Player One", "P1"]` |
| `first_seen` | `str` | ISO 8601 timestamp of earliest message | `"2024-01-01T10:00:00+00:00"` |
| `last_seen` | `str` | ISO 8601 timestamp of most recent message | `"2024-06-30T22:15:00+00:00"` |
| `msg_count` | `int` | Total number of messages authored | `1240` |
| `tuppers_owned` | `list[str]` | Slugs of characters proxied by this player | `["alexis-snyder", "tamura"]` |

---

## 4. `characters/private/<slug>.yaml`

**File pattern:** `characters/private/<slug>.yaml`
**Source:** `scripts/import_tupperbox.py`
**Format:** YAML, UTF-8. One file per character. Slug = lowercase-hyphenated name.

| Field | Type | Description | Example |
|---|---|---|---|
| `name` | `str` | Character display name | `"Alexis Snyder"` |
| `slug` | `str` | URL-safe identifier derived from name | `"alexis-snyder"` |
| `group` | `str \| null` | Tupperbox group name; null if ungrouped | `"NPCs"` |
| `description` | `str \| null` | Free-text character description/bio | `"Human\nAlexis is a tall..."` |
| `avatar_url` | `str \| null` | CDN URL of character avatar image | `"https://cdn.tupperbox.app/pfp/..."` |
| `brackets` | `list[str]` | Proxy trigger brackets (prefix, suffix pair) | `["Alexis:", ""]` |
| `posts_count` | `int` | Number of posts made via Tupperbox | `0` |
| `last_used` | `str \| null` | ISO 8601 timestamp of last proxy use; null if never | `null` |
| `tupperbox_id` | `int` | Numeric Tupperbox internal ID | `152262807` |
| `player_status` | `str` | Enum: `member_current` / `former_member` / `unknown` (eredita dallo owner player). Default null. | `"former_member"` |
| `active` | `bool` | `true` se `player_status=member_current` AND `char_used_in_last_6mo`. Default null. | `true` |
| `last_updated_physical` | `str (ISO date)` | Data ultimo aggiornamento campo physical description | `"2024-03-15"` |
| `last_updated_lore` | `str (ISO date)` | Data ultimo aggiornamento campo lore/backstory | `"2023-11-02"` |
| `last_updated_voice` | `str (ISO date)` | Data ultimo aggiornamento campo voice/brackets | `"2024-01-20"` |

> `last_updated_*` fields enable recency-weighted merging when multiple sources update the same character. More recent field-group wins in conflict resolution. Populated by import pipeline or operator manually.

**Example (`characters/private/alexis-snyder.yaml`):**
```yaml
name: Alexis Snyder
slug: alexis-snyder
group: NPCs
description: "Human\nAlexis is a tall, slim woman standing around six feet (183 cm)..."
avatar_url: https://cdn.tupperbox.app/pfp/603341648360898581/Kke7sJT7hAOVx0gr.webp
brackets:
  - 'Alexis:'
  - ''
posts_count: 0
last_used: null
tupperbox_id: 152262807
```

---

## 5. `characters/<slug>.canon.yaml` — Runtime Attribute Override (Q3)

Runtime per-attribute override file. Created manually by operator or by future `canon-tune` CLI (M3, not implemented). Schema scaffold only.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `slug` | `str` | Must match parent `<slug>.yaml` | `"alexis-snyder"` |
| `canon_version` | `str` | Schema version | `"1.0"` |
| `overrides` | `list[CanonField]` | Per-attribute override entries | see below |

**CanonField schema:**

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `field_path` | `str` | Dotted path into parent YAML | `"description"` / `"voice.pitch"` |
| `value` | `any` | Override value (replaces parent at runtime) | `"Low, husky voice"` |
| `tier` | `str` | `CANON` (locked, authoritative) / `SOFT` (default, tunable) | `"SOFT"` |
| `source` | `str` | Origin of override (`operator` / `mcp` / `scene_inference`) | `"operator"` |
| `since` | `str (ISO date)` | When override was set | `"2024-05-17"` |
| `note` | `str\|null` | Free-text rationale | `"Corrected after scene 142"` |

**Tier semantics:**
- `CANON`: hard override — never overwritten by import pipeline or inference
- `SOFT`: soft override — can be updated by MCP inference if newer evidence found

**Example canon.yaml:**
```yaml
slug: alexis-snyder
canon_version: "1.0"
overrides:
  - field_path: description
    value: "Alexis is a skilled archer..."
    tier: SOFT
    source: operator
    since: "2024-05-17"
    note: null
  - field_path: voice.pitch
    value: "Low, controlled"
    tier: CANON
    source: operator
    since: "2024-05-17"
    note: "Confirmed in scene 089"
```

---

## 6. ChromaDB Collections

**DB path:** `.chroma_calliope/`
**Source:** `scripts/build_chromadb_index.py`
**Backend:** ChromaDB persistent client.

> **Metadata type constraint:** ChromaDB accepts only `str`, `int`, `float`, `bool` as metadata values.
> Lists (e.g. character lists, flag lists) must be serialized as comma-separated strings.

### 6.1 `calliope_messages`

Indexes individual messages (or chunks for messages > 2 000 characters).

| Field | Kind | Type | Description | Example |
|---|---|---|---|---|
| `document` | document | `str` | Message `content`; chunked with suffix `:chunkN` if long | `"Alexis: Buonasera, cosa posso portarvi?"` |
| `id` | id | `str` | `calliope_messages:<message_id>` or `calliope_messages:<message_id>:chunk0` | `"calliope_messages:1320593702623772756"` |
| `channel_id` | metadata | `str` | Source channel snowflake ID | `"1312211590883442688"` |
| `author_id` | metadata | `str` | Author snowflake ID | `"603341648360898581"` |
| `timestamp` | metadata | `str` | ISO 8601 creation timestamp | `"2024-01-15T18:32:04.123+00:00"` |
| `tag` | metadata | `str` | `IC`, `OOC`, or `system` | `"IC"` |
| `tupperbox_proxy` | metadata | `str` | `"true"` or `"false"` (serialized bool) | `"true"` |
| `parent_channel_id` | metadata | `str` | Parent channel ID or `""` for top-level | `""` |
| `player_status` | metadata | `str` | `member_current` / `former_member` / `unknown` / `""` (null) | `"member_current"` |

### 6.2 `calliope_characters`

Indexes character cards for semantic lookup by name, group, or description.

| Field | Kind | Type | Description | Example |
|---|---|---|---|---|
| `document` | document | `str` | Concatenation: `"<name> <group> <description>"` | `"Alexis Snyder NPCs Human\nAlexis is..."` |
| `id` | id | `str` | `calliope_characters:<slug>` | `"calliope_characters:alexis-snyder"` |
| `slug` | metadata | `str` | Character slug | `"alexis-snyder"` |
| `group` | metadata | `str` | Group name or `""` if null | `"NPCs"` |
| `tupperbox_id` | metadata | `str` | Tupperbox numeric ID as string | `"152262807"` |
| `posts_count` | metadata | `str` | Post count as string | `"0"` |
| `avatar_url` | metadata | `str` | CDN avatar URL or `""` if null | `"https://cdn.tupperbox.app/..."` |
| `player_status` | metadata | `str` | `member_current` / `former_member` / `unknown` / `""` | `"member_current"` |
| `active` | metadata | `str` | `"true"` / `"false"` / `""` (ChromaDB serializza bool→str) | `"true"` |

### 6.3 `calliope_scenes`

Indexes extracted scene summaries for narrative retrieval.

| Field | Kind | Type | Description | Example |
|---|---|---|---|---|
| `document` | document | `str` | Scene summary text | `"La festa inizia nella taverna di Yorend..."` |
| `id` | id | `str` | `calliope_scenes:<scene_id>` | `"calliope_scenes:042"` |
| `scene_id` | metadata | `str` | Scene identifier | `"042"` |
| `timestamp_range` | metadata | `str` | ISO 8601 range: `"<start>/<end>"` | `"2024-01-15T18:00:00+00:00/2024-01-15T22:00:00+00:00"` |
| `char_list` | metadata | `str` | Comma-separated character slugs present | `"alexis-snyder,tamura,yorend-gm"` |
| `msg_count` | metadata | `str` | Number of messages in the scene | `"47"` |

---

## Retrieval Filters

| Use-case | Filter | Rationale |
|----------|--------|-----------|
| Scene generation | `active=true` | Exclude inactive chars/former players |
| Training corpus | (no filter) | Include full history for style training |
| Character lookup | `player_status != former_member` | Default, operator can override |

Note: `active` field available only after `extract_member_list.py` is run (dispatch separate). Default null = unfiltered until populated.

---

## Note Tecniche

### ChromaDB — vincoli sui tipi di metadati

ChromaDB accetta esclusivamente `str`, `int`, `float`, `bool` come valori di metadati.
Tipi Python non supportati:
- `list` → serializzare come stringa con join (es. `",".join(items)`)
- `None` → usare `""` (stringa vuota) come sentinel
- `dict` → non supportato, appiattire in campi separati

### ID format

Tutti gli ID seguono il pattern `<collection>:<key>[:suffisso]`:
- Nessuno spazio, nessun carattere speciale eccetto `:` e `-`
- Chunk index è 0-based: `chunk0`, `chunk1`, …

### Encoding

Tutti i file sono UTF-8 senza BOM. Il flag `ensure_ascii=False` è usato nei writer JSONL
per preservare caratteri Unicode (emoji, caratteri accentati italiani).

### Campi futuri

`players.jsonl` verrà generato da un aggregation script non ancora implementato.
Fino ad allora, le informazioni sui player si ricavano da `messages_clean.jsonl`
filtrando per `author_id` e `tupperbox_proxy == false`.

`player_status` e `active` saranno popolati da `extract_member_list.py` (sprint separato, pending operator). Defaults a null = no filter impact fino a popolamento.

## Narrative State Schema (`narrative_state.json`)

**File**: `.planning/narrative_state.json` — cross-scene persistence updated by `NarrativeState.update_from_scene()` (cerebras via gateway).

### Top-level fields

| Field | Type | Description |
|-------|------|-------------|
| `chars` | `dict[str, CharState]` | Per-char state keyed by name |
| `plot_threads` | `list[PlotThread]` | Active/resolved/abandoned arcs |
| `current_location` | `str` | In-fiction current location |
| `current_time` | `str` | In-fiction time marker |
| `scene_count` | `int` | Number of scenes processed |

### CharState

| Field | Type | Valid values |
|-------|------|-------------|
| `name` | `str` | Character name |
| `emotion` | `str` | `neutral\|happy\|sad\|angry\|fearful\|determined\|wounded` |
| `location` | `str` | In-fiction location |
| `status` | `str` | `alive\|wounded\|dead\|missing\|unknown` |
| `last_interaction` | `str` | Last scene_type where mentioned |

### PlotThread

| Field | Type | Valid values |
|-------|------|-------------|
| `name` | `str` | Short thread identifier |
| `description` | `str` | Thread description |
| `status` | `str` | `active\|resolved\|abandoned` |
| `scenes_mentioned` | `list[str]` | Scene numbers as strings |
| `last_updated` | `str` | e.g. `"scene_3"` |

### Example
```json
{
  "chars": {
    "Aurora": {"name": "Aurora", "emotion": "determined", "location": "palace gardens",
               "status": "wounded", "last_interaction": "action_combat"}
  },
  "plot_threads": [
    {"name": "assassin arc", "description": "Aurora hunts the palace assassin",
     "status": "active", "scenes_mentioned": ["1", "2"], "last_updated": "scene_2"}
  ],
  "current_location": "palace gardens",
  "current_time": "night",
  "scene_count": 4
}
```
