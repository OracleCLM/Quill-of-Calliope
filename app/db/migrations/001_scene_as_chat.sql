-- Calliope — DB Schema Scene-as-Chat
-- Migration 001: tabelle core (P1 target schema)
-- Source spec: docs/p0_foundation/DB_SCHEMA_SCENE_AS_CHAT.md
-- Generato: 2026-06-03 | sprint: EFESTO-CAL-DDL-01

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ---------------------------------------------------------------------------
-- arcs: raggruppamento logico di scene
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS arcs (
    id          TEXT PRIMARY KEY,           -- UUID (app-generated)
    title       TEXT NOT NULL,
    description TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- ---------------------------------------------------------------------------
-- scenes: chat multi-personaggio — core del sistema
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scenes (
    id               TEXT PRIMARY KEY,
    arc_id           TEXT REFERENCES arcs(id) ON DELETE SET NULL,
    title            TEXT NOT NULL,
    location         TEXT,
    is_readonly      INTEGER NOT NULL DEFAULT 0,  -- 1 per scene legacy da dataset
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    last_activity_at TEXT                         -- per sorting dashboard
);

CREATE INDEX IF NOT EXISTS idx_scenes_arc_id ON scenes(arc_id);
CREATE INDEX IF NOT EXISTS idx_scenes_last_activity ON scenes(last_activity_at DESC);

-- ---------------------------------------------------------------------------
-- characters: schede personaggio (Character Card V2/V3 compatible)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS characters (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    card_json  TEXT,                        -- JSON blob V2/V3 spec
    image_path TEXT,
    kind       TEXT NOT NULL DEFAULT 'npc'
                   CHECK (kind IN ('operator','player','npc')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- ---------------------------------------------------------------------------
-- scene_characters: junction scene N-M characters
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scene_characters (
    scene_id     TEXT NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    character_id TEXT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    role         TEXT NOT NULL DEFAULT 'participant',
    joined_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    PRIMARY KEY (scene_id, character_id)
);

CREATE INDEX IF NOT EXISTS idx_scene_chars_char ON scene_characters(character_id);

-- ---------------------------------------------------------------------------
-- messages: log cronologico messaggi di scena
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
    id                TEXT PRIMARY KEY,
    scene_id          TEXT NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    character_id      TEXT REFERENCES characters(id) ON DELETE SET NULL,  -- NULL = Discord senza char
    author_name       TEXT,                 -- denorm per discord scraping
    content_original  TEXT,
    content_enhanced  TEXT,                 -- output post-AI enhance (nullable)
    ts                TEXT NOT NULL,
    source            TEXT NOT NULL DEFAULT 'manual'
                          CHECK (source IN ('manual','discord_scrape','ai_draft')),
    position_order    INTEGER NOT NULL DEFAULT 0,
    is_summary        INTEGER NOT NULL DEFAULT 0   -- 1 = auto-summarize di range precedente
);

CREATE INDEX IF NOT EXISTS idx_messages_scene_id ON messages(scene_id, position_order);
CREATE INDEX IF NOT EXISTS idx_messages_character ON messages(character_id);
CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(ts);

-- ---------------------------------------------------------------------------
-- lore_entries: knowledge base operator-curata
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lore_entries (
    id          TEXT PRIMARY KEY,
    category    TEXT NOT NULL DEFAULT 'other'
                    CHECK (category IN (
                        'world_setting','places','characters_events',
                        'mechanics_magic','other'
                    )),
    title       TEXT NOT NULL,
    content_text TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    created_by  TEXT NOT NULL DEFAULT 'operator'
);

CREATE INDEX IF NOT EXISTS idx_lore_category ON lore_entries(category);

-- ---------------------------------------------------------------------------
-- arc_lore: junction arc N-M lore_entries
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS arc_lore (
    arc_id        TEXT NOT NULL REFERENCES arcs(id) ON DELETE CASCADE,
    lore_entry_id TEXT NOT NULL REFERENCES lore_entries(id) ON DELETE CASCADE,
    PRIMARY KEY (arc_id, lore_entry_id)
);
